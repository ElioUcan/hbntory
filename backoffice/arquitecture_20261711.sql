create extension if not exists pgcrypto;


CREATE OR REPLACE TABLE users (
    user_id generated always as identity primary key, --identification of user
    user_role text not null, --role of the user admin/common
    branch text not null foreign key, --branch asigned
    created_at TIMESTAMP not null, --creation of the role
    updated_at TIMESTAMP not null, --update state
    status text not null, --active or deleted
    password text not null, --NEEDS HASH

);

CREATE OR REPLACE TABLE branches (
    user_id integer not null foreign key, --user id
    branch text not null primary key, --branch name
    stock integer not null, --number of stocks

    constraint not_zero check (stock > 0) --stocks can be negative
);
-- stock cant be negative CHECK
-- stock changes require positive integer quantities NOT
-- stock operations reference valid branches NOT
-- Stock operations reference product identifiers that exist in the external Product API
-- when applicable NOT
create or replace function validate_stocks()
return trigger as $$
declare
    validation;
begin
