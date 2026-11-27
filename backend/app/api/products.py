"""Mahsulotlar katalogi."""

from fastapi import APIRouter, File, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

from app.api.deps import SessionDep, not_found
from app.core.config import get_settings
from app.core.files import atomic_write_bytes
from app.models.catalog import Annotation, ModelVersion, Product

router = APIRouter(prefix="/products", tags=["products"])


class ProductIn(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    category: str | None = Field(default=None, max_length=100)


class ProductOut(ProductIn):
    id: int
    has_image: bool
    objects: int = 0
    active_version: int | None = None


async def _out(session, products: list[Product]) -> list[ProductOut]:
    ids = [p.id for p in products]
    counts: dict[int, int] = {}
    active: dict[int, int] = {}
    if ids:
        counts = dict(
            (
                await session.execute(
                    select(Annotation.product_id, func.count())
                    .where(Annotation.product_id.in_(ids))
                    .group_by(Annotation.product_id)
                )
            ).all()
        )
        active = dict(
            (
                await session.execute(
                    select(ModelVersion.product_id, ModelVersion.version).where(
                        ModelVersion.product_id.in_(ids), ModelVersion.is_active.is_(True)
                    )
                )
            ).all()
        )
    return [
        ProductOut(
            id=p.id,
            code=p.code,
            name=p.name,
            category=p.category,
            has_image=bool(p.image_path),
            objects=counts.get(p.id, 0),
            active_version=active.get(p.id),
        )
        for p in products
    ]


@router.get("", response_model=list[ProductOut])
async def list_products(session: SessionDep, q: str | None = None, category: str | None = None) -> list[ProductOut]:
    stmt = select(Product).order_by(Product.name)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Product.name.ilike(like), Product.code.ilike(like)))
    if category:
        stmt = stmt.where(Product.category == category)
    return await _out(session, list((await session.execute(stmt)).scalars()))


@router.get("/categories", response_model=list[str])
async def categories(session: SessionDep) -> list[str]:
    rows = await session.execute(
        select(Product.category).where(Product.category.isnot(None)).distinct().order_by(Product.category)
    )
    return [r for (r,) in rows]


@router.get("/{product_id}", response_model=ProductOut)
async def get_product(product_id: int, session: SessionDep) -> ProductOut:
    p = await session.get(Product, product_id)
    if p is None:
        raise not_found("Mahsulot topilmadi")
    return (await _out(session, [p]))[0]


@router.post("", response_model=ProductOut, status_code=201)
async def create_product(data: ProductIn, session: SessionDep) -> ProductOut:
    p = Product(code=data.code.strip(), name=data.name.strip(), category=(data.category or "").strip() or None)
    session.add(p)
    try:
        await session.commit()
    except IntegrityError as e:
        raise HTTPException(409, f"'{data.code}' kodli mahsulot allaqachon bor") from e
    return (await _out(session, [p]))[0]


@router.patch("/{product_id}", response_model=ProductOut)
async def update_product(product_id: int, data: ProductIn, session: SessionDep) -> ProductOut:
    p = await session.get(Product, product_id)
    if p is None:
        raise not_found("Mahsulot topilmadi")
    p.code, p.name, p.category = data.code.strip(), data.name.strip(), (data.category or "").strip() or None
    try:
        await session.commit()
    except IntegrityError as e:
        raise HTTPException(409, f"'{data.code}' kodli mahsulot allaqachon bor") from e
    return (await _out(session, [p]))[0]


@router.delete("/{product_id}", status_code=204)
async def delete_product(product_id: int, session: SessionDep) -> Response:
    p = await session.get(Product, product_id)
    if p is None:
        raise not_found("Mahsulot topilmadi")
    await session.delete(p)
    await session.commit()
    return Response(status_code=204)


@router.put("/{product_id}/image", response_model=ProductOut)
async def upload_image(product_id: int, session: SessionDep, file: UploadFile = File(...)) -> ProductOut:
    p = await session.get(Product, product_id)
    if p is None:
        raise not_found("Mahsulot topilmadi")
    data = await file.read()
    if len(data) > 10 * 2**20:
        raise HTTPException(413, "Rasm juda katta (10 MB gacha)")
    ext = ".png" if (file.content_type or "").endswith("png") else ".jpg"
    rel = f"products/{product_id}{ext}"
    atomic_write_bytes(get_settings().data_path / rel, data)
    p.image_path = rel
    await session.commit()
    return (await _out(session, [p]))[0]


@router.get("/{product_id}/image")
async def get_image(product_id: int, session: SessionDep) -> FileResponse:
    p = await session.get(Product, product_id)
    if p is None or not p.image_path:
        raise not_found("Rasm yo'q")
    return FileResponse(get_settings().data_path / p.image_path, headers={"Cache-Control": "no-cache"})
