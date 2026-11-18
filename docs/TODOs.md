backoffice: used to aunthenticate the users and manage stock
Clien web UI: where users can ask questions about products and stock using natural language

- Postgres para las base de datos relacional
- aunthentication con fastapi
- external apis
- AI agents con adk de google
- mcp con fastapi
- Sistema de microservicios

Implementar:
- authentication
- Rbac
- api para consumir
- mcp
- agentes de ia
- rest o websocket(usaremos rest)

The Backoffice database will only store local system data, such as users, branches, and stock quantities associated with product identifiers.


Para conseguir los datos de los productos se me va a dar un container de docker el cual ya tiene la api. En la api la cual es read only puedo:
- listar todos los productos disponibles
- obtener detalles de un producto en especifico

El sistema debe de usar esta api, cada que se necesite informacion de un producto

# High level system components

## Servicios de backoffice
1. Una aplicacion web con autenticacion interna
2. Manejar usuraios y la branch stock
3. Usar sqlalchemy para acceder a la DB
## Relational database
1. Guardar usuarios, ramas, y la cantidad de stock
2. No guarda los detalles de los productos
##  External Product API
1. Nos da un container de docker
2. Es una fuente read-only
## Product MCP server
1. implementado por mi equipo
2. actua como un puente entre el sistema de IA y la API de Productos
## AI Query Service
1. Servicio independiente del backend
2. Contiene 1 o mas agentes
3. Procesa preguntas de lenguaje natural desde el Client Web Interface
## Client web interface
- Un simple chat o caja de busqueda
- Permite a usuarios anonimos preguntar acerca de los productos y el stock

# Mandatory Functional Scope
## Backoffice: Common Users
Los usuarios comunes deben ser asignados solo a 1 branch
Un usuario comun solo puede operar en el stock de la branch asignada
Un usuario comun puede:
- add stock
- quitar stock
- consultar stock
- listar los productos que estan en stock en su rama
## Admin user
Solo puede haber 1 admin
No implementar funcionalidades para add mas admins
El admin puede:
- Listar usuarios
- Crear usuarios comunes
- asignar usuarios comunes a ramas
- soft-delete usuarios
- modificar usuarios
- cambiar la password de un usuario
- cambiar la rama asignada de ese usuario
El admin no maneja el stock

## Product Data
La informacion del producto proviene de la APi exsterna
LA db no almacena nada que tenga que ver con productos: nombres, descripcipones, precios, imagenes, metadata, NADA.

SOLO guarda el id del producto necesario para asociarlo a un producto.

## Stock data
El sistema debe guardad cantidades por rama y producto.
Como minimo el stock model debe soportar:
- identificacion de la rama
- identificiacion del producto
- cantidad disponible
La cantidad disponible nunca puede ser negativa
Add o quitar stock debe validar la cantidad requestada

## Auth y Autorizacion
La backoffice necesita auth y autho.
Las reglas de esto deben ser definidas en el backend no solo en la UI.
Las passwords se deben almacenar de manera segura en la DB
Nada de passwords almacenadas como TEXT
El equipo debe de explicar:
- Que passwords hasing mechanism fue usado
- Porque esto es apropiado para passwords almacenadas
- Como se hace la auntenticacion
- Como se aplica el RBAC
Para este proyecto no se necesita SSL ni TLS.

## UI
PAgina simple donde usuarios anonimos pueden preguntar usando lenguaje natural acerca de productos.

No es necesarion un login.

Cada pregunta se trata de manera independiente. No se necesita llevar historial.
Preguntas de ejemplo:
“Which branch has stock of product X?”
“What products can I find in branch Y?”
“If I want to buy 3 units of X, 2 units of Y, and 4 units of Z, which branch or branches should I visit?”
“Give me details about product XX.”

La interfaz debe ser:
- Un chat style
- Una search box style interface
El design debe ser useful y functional

## Client communication Strat.

- Rest api, para preguntas simples
- websocket para real-time behaviour.

## AI Query service
Independiente del backoffice.
Minimo 1 agente de IA. 
El sistema debe responder preguntas usando:
- datos de producto de la api usando un mcp 
- datos de el stock de la db usando un mcp.
El agente no debe inventar info, y si no tiene info debe decirlo.

## MCP requirements
Actua como un puente entre el product API
Debe:
- listar los productos
- retornar detales de productos.

Ademas el equipo debe decidir como el AI system accedera al stock de la informacion

Pueden:
- Extender el propio MCP server para dar control de las queries de stck
- Usar otro mcp especializado para DBs como MCP Toolbox for Databases,
Deben justificar su decision.
