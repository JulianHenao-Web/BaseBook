-- =========================================
-- TABLA DE LIBROS
-- =========================================

create table libros (
  isbn text primary key,
  titulo text not null,
  autor text,
  anio int,
  portada text,
  tema text,
  total_ejemplares int not null default 1
    check (total_ejemplares >= 0),
  ejemplares_disponibles int not null default 1,
  estado text not null default 'activo'
    check (estado in ('activo', 'inactivo')),
  creado_en timestamptz not null default now(),
  constraint ejemplares_validos
    check (ejemplares_disponibles between 0 and total_ejemplares)
);

-- Funcion para descontar ejemplares
create function descontar_ejemplar(p_isbn text)
returns setof libros as $$
  update libros
  set ejemplares_disponibles = ejemplares_disponibles - 1
  where isbn = p_isbn and ejemplares_disponibles > 0
  returning *;
$$ language sql;

-- Funcion para devolver ejemplares
create function devolver_ejemplar(p_isbn text)
returns setof libros as $$
  update libros
  set ejemplares_disponibles = ejemplares_disponibles + 1
  where isbn = p_isbn
    and ejemplares_disponibles < total_ejemplares
  returning *;
$$ language sql;


-- =========================================
-- TABLA DE PARAMETROS
-- =========================================

create table parametros (
    clave text primary key,
    valor integer not null,
    actualizado_en timestamptz not null default now(),
    actualizado_por uuid references usuarios(id)
);


-- =========================================
-- TABLA DE PRESTAMOS
-- =========================================

create table prestamos (
    id bigserial primary key,
    usuario_id uuid not null references usuarios(id),
    isbn text not null references libros(isbn),
    fecha_prestamo date not null default current_date,
    fecha_limite date not null,
    fecha_devolucion date,
    estado text not null default 'activo'
        check (estado in ('activo', 'devuelto')),
    registrado_por uuid references usuarios(id)
);


-- =========================================
-- TABLA DE MULTAS
-- =========================================

create table multas (
    id bigserial primary key,
    prestamo_id bigint not null unique references prestamos(id),
    usuario_id uuid not null references usuarios(id),
    dias_retraso integer not null check (dias_retraso > 0),
    valor_dia integer not null check (valor_dia >= 0),
    monto integer not null check (monto >= 0),
    estado text not null default 'pendiente'
        check (estado in ('pendiente', 'pagada')),
    fecha_generacion date not null default current_date,
    fecha_pago date
);

-- Indice para consultar multas por usuario y estado
create index idx_multas_usuario_estado
on multas (usuario_id, estado);