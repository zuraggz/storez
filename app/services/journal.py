"""Journal (blog) queries."""

from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import BlogPost


def list_posts(session: Session, limit: int = 6) -> list[BlogPost]:
    limit = 6 if limit < 1 or limit > 50 else limit

    return list(
        session.scalars(
            select(BlogPost).order_by(BlogPost.published_at.desc(), BlogPost.id.desc()).limit(limit)
        )
    )


def get_post_by_slug(session: Session, slug: str) -> BlogPost | None:
    return session.scalars(select(BlogPost).where(BlogPost.slug == slug)).first()


def record_post_view(session: Session, post_id: int) -> None:
    session.execute(
        update(BlogPost).where(BlogPost.id == post_id).values(views=BlogPost.views + 1)
    )
    session.commit()
