-- Tabla de usuarios para login (BD de autenticación local).
-- Se ejecuta solo la primera vez que se crea el volumen (initdb).

CREATE TABLE IF NOT EXISTS public.usuarios (
    id          SERIAL PRIMARY KEY,
    usuario     VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    nombre      VARCHAR(255),
    rol         VARCHAR(50) DEFAULT 'usuario',
    activo      BOOLEAN DEFAULT true,
    creado_en   TIMESTAMPTZ DEFAULT now(),
    actualizado_en TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_usuarios_usuario ON public.usuarios(usuario);
CREATE INDEX IF NOT EXISTS idx_usuarios_activo ON public.usuarios(activo);

COMMENT ON TABLE public.usuarios IS 'Usuarios para login; BD local en el servidor (postgres-auth).';
