from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from app.models.framework import (
    Framework,
    FrameworkFunction,
    FrameworkCategory,
    FrameworkSubcategory,
)


class FrameworkService:
    @staticmethod
    def list_frameworks(db: Session) -> List[dict]:
        frameworks = db.query(Framework).all()
        results = []
        for fw in frameworks:
            fn_count = db.query(FrameworkFunction).filter(FrameworkFunction.framework_id == fw.id).count()
            cat_count = (
                db.query(FrameworkCategory)
                .join(FrameworkFunction, FrameworkCategory.function_id == FrameworkFunction.id)
                .filter(FrameworkFunction.framework_id == fw.id)
                .count()
            )
            sub_count = (
                db.query(FrameworkSubcategory)
                .join(FrameworkCategory, FrameworkSubcategory.category_id == FrameworkCategory.id)
                .join(FrameworkFunction, FrameworkCategory.function_id == FrameworkFunction.id)
                .filter(FrameworkFunction.framework_id == fw.id)
                .count()
            )
            results.append({
                "id": fw.id,
                "identifier": fw.identifier,
                "name": fw.name,
                "version": fw.version,
                "description": fw.description,
                "created_at": fw.created_at,
                "total_functions": fn_count,
                "total_categories": cat_count,
                "total_subcategories": sub_count,
            })
        return results

    @staticmethod
    def get_by_id(db: Session, framework_id: int) -> Optional[Framework]:
        return db.query(Framework).filter(Framework.id == framework_id).first()

    @staticmethod
    def get_tree(db: Session, framework_id: int) -> Optional[Framework]:
        return (
            db.query(Framework)
            .filter(Framework.id == framework_id)
            .options(
                joinedload(Framework.functions)
                .joinedload(FrameworkFunction.categories)
                .joinedload(FrameworkCategory.subcategories)
            )
            .first()
        )