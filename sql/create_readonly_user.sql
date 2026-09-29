-- Crea un login de SOLO LECTURA para los reportes.
-- Ejecutar UNA vez en SSMS (en la VM Windows), conectado como sa a <servidor>\NATIONALSOFT.
-- 1) Reemplaza <CONTRASENA_FUERTE> por una contraseña nueva (NO la de sa).
-- 2) Escribe esa misma contraseña en SR_DB_PASSWORD del archivo .env en la Mac.

USE master;
GO
CREATE LOGIN reportes_ro
    WITH PASSWORD = N'<CONTRASENA_FUERTE>',
         DEFAULT_DATABASE = softrestaurant11,
         CHECK_POLICY = ON;
GO

USE softrestaurant11;
GO
CREATE USER reportes_ro FOR LOGIN reportes_ro;
GO
-- Leer todas las tablas/vistas
ALTER ROLE db_datareader ADD MEMBER reportes_ro;
-- Bloquear explícitamente cualquier INSERT/UPDATE/DELETE
ALTER ROLE db_denydatawriter ADD MEMBER reportes_ro;
-- Ver el código de vistas y stored procedures (para entender cómo SR arma sus reportes)
GRANT VIEW DEFINITION TO reportes_ro;
GO

-- Nota: si ALTER ROLE ... ADD MEMBER marca error (SQL Server 2008 o anterior), usa:
--   EXEC sp_addrolemember 'db_datareader', 'reportes_ro';
--   EXEC sp_addrolemember 'db_denydatawriter', 'reportes_ro';

-- Verificación (debe listar db_datareader y db_denydatawriter):
SELECT r.name AS rol
FROM sys.database_role_members m
JOIN sys.database_principals r ON r.principal_id = m.role_principal_id
JOIN sys.database_principals u ON u.principal_id = m.member_principal_id
WHERE u.name = 'reportes_ro';
GO
