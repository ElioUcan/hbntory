from pathlib import Path
from typing import Annotated
from urllib.parse import quote

import requests
from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from hbentory.backoffice.db import Branches, Roles, Stock, Users
from hbentory.backoffice.deps import (
    get_current_active_user,
    get_db,
    require_admin,
    require_common_user,
)
from hbentory.backoffice.schemas import (
    BranchResponse,
    MeResponse,
    StockResponse,
    StockUpdate,
    Token,
    UserCreate,
    UserResponse,
    UserUpdate,
)
from hbentory.backoffice.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from hbentory.backoffice.seed import PRODUCT_API_URL, update_stock

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="HBentory Backoffice")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def _fetch_product_api(path: str, params: dict[str, int | str] | None = None) -> dict[str, object]:
    """Query the external Product API and map upstream errors to HTTP responses."""
    try:
        response = requests.get(f"{PRODUCT_API_URL}{path}", params=params, timeout=3)
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Product API unavailable",
        ) from exc

    if response.status_code == status.HTTP_404_NOT_FOUND:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    if response.status_code >= 500:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Product API unavailable",
        )
    if response.status_code != status.HTTP_200_OK:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unexpected response from Product API",
        )
    return response.json()


def _get_modifiable_common_user(db: Session, user_id: int, admin_user: Users) -> Users:
    target = db.scalar(
        select(Users).options(joinedload(Users.role)).where(Users.user_id == user_id)
    )
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if target.user_id == admin_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Admin cannot modify own account"
        )
    if target.role is None or target.role.name != "common":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only common users can be modified"
        )
    return target


def _commit_user(db: Session, user: Users) -> Users:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User conflict") from exc
    db.refresh(user)
    return user


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/auth/login", response_model=Token)
def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)],
) -> Token:
    user = db.scalar(select(Users).where(Users.username == form_data.username))
    if (
        user is None
        or user.status != "active"
        or not verify_password(form_data.password, user.password_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(access_token=create_access_token(user.user_id))


@app.get("/auth/me", response_model=MeResponse)
def auth_me(current_user: Annotated[Users, Depends(get_current_active_user)]) -> MeResponse:
    return MeResponse(
        **UserResponse.model_validate(current_user).model_dump(),
        role_name=current_user.role.name,
        branch=current_user.branch,
    )


@app.get("/products")
def list_products(
    current_user: Annotated[Users, Depends(get_current_active_user)],
    q: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, object]:
    params: dict[str, int | str] = {"limit": limit, "offset": offset}
    if q is not None and q.strip():
        params["q"] = q.strip()
    return _fetch_product_api("/api/v1/products", params=params)


@app.get("/products/{id_or_sku}")
def get_product_detail(
    id_or_sku: str,
    current_user: Annotated[Users, Depends(get_current_active_user)],
) -> dict[str, object]:
    cleaned = id_or_sku.strip()
    if not cleaned:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product identifier cannot be empty",
        )
    return _fetch_product_api(f"/api/v1/products/{quote(cleaned, safe='')}")

@app.get('/branches', response_model=list[BranchResponse])
def get_branches(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[Users, Depends(get_current_active_user)]
) -> list[Branches]:
    return list(db.scalars(select(Branches).order_by(Branches.branch_id)).all())

@app.get("/users", response_model=list[UserResponse])
def list_users(
    db: Annotated[Session, Depends(get_db)],
    admin_user: Annotated[Users, Depends(require_admin)],
) -> list[Users]:
    return list(db.scalars(select(Users).order_by(Users.user_id)).all())


@app.post("/users", status_code=status.HTTP_201_CREATED, response_model=UserResponse)
def create_user(
    payload: UserCreate,
    db: Annotated[Session, Depends(get_db)],
    admin_user: Annotated[Users, Depends(require_admin)],
) -> Users:
    if db.scalar(select(Users.user_id).where(Users.username == payload.username)) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")
    if db.get(Branches, payload.branch_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found")
    common_role = db.scalar(select(Roles).where(Roles.name == "common"))
    if common_role is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Common role not found"
        )

    user = Users(
        username=payload.username,
        password_hash=hash_password(payload.password),
        role_id=common_role.role_id,
        branch_id=payload.branch_id,
        status="active",
    )
    db.add(user)
    return _commit_user(db, user)


@app.patch("/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Annotated[Session, Depends(get_db)],
    admin_user: Annotated[Users, Depends(require_admin)],
) -> Users:
    target = _get_modifiable_common_user(db, user_id, admin_user)

    username: str | None = None
    if payload.username is not None:
        username = payload.username.strip()
        if not username:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Username cannot be blank",
            )
        conflict_id = db.scalar(
            select(Users.user_id).where(
                Users.username == username, Users.user_id != user_id
            )
        )
        if conflict_id is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Username already exists"
            )
    if payload.branch_id is not None and db.get(Branches, payload.branch_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found")

    if username is not None:
        target.username = username
    if payload.password is not None:
        target.password_hash = hash_password(payload.password)
    if payload.branch_id is not None:
        target.branch_id = payload.branch_id
    if payload.status is not None:
        target.status = payload.status
    return _commit_user(db, target)


@app.delete("/users/{user_id}", response_model=UserResponse)
def delete_user(
    user_id: int,
    db: Annotated[Session, Depends(get_db)],
    admin_user: Annotated[Users, Depends(require_admin)],
) -> Users:
    target = _get_modifiable_common_user(db, user_id, admin_user)
    target.status = "deleted"
    db.commit()
    db.refresh(target)
    return target


@app.get("/stock", response_model=list[StockResponse])
def list_stock(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[Users, Depends(require_common_user)],
    in_stock_only: bool = False,
) -> list[Stock]:
    stmt = select(Stock).where(Stock.branch_id == current_user.branch_id)
    if in_stock_only:
        stmt = stmt.where(Stock.quantity > 0)
    return list(db.scalars(stmt.order_by(Stock.product_id)).all())


@app.get("/stock/{product_id}", response_model=StockResponse)
def get_stock_item(
    product_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[Users, Depends(require_common_user)],
) -> Stock:
    stock = db.scalar(
        select(Stock).where(
            Stock.branch_id == current_user.branch_id, Stock.product_id == product_id
        )
    )
    if stock is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock item not found")
    return stock


@app.post("/stock", response_model=StockResponse)
def modify_stock(
    payload: StockUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[Users, Depends(require_common_user)],
) -> Stock:
    try:
        stock = update_stock(
            db,
            branch_id=current_user.branch_id,
            product_id=payload.product_id,
            quantity=payload.quantity,
            operation=payload.operation,
        )
        db.commit()
        db.refresh(stock)
    except ValueError as exc:
        db.rollback()
        code = (
            status.HTTP_503_SERVICE_UNAVAILABLE
            if "unavailable" in str(exc).lower()
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=code, detail=str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Stock conflict") from exc
    return stock
