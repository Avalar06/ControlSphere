from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from app.db.base import Base


class Framework(Base):
    __tablename__ = "frameworks"

    id = Column(Integer, primary_key=True, index=True)
    identifier = Column(String(50), unique=True, index=True, nullable=False)  # e.g., "NIST-CSF-2.0"
    name = Column(String(255), nullable=False)
    version = Column(String(20), nullable=False, default="2.0")
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    functions = relationship("FrameworkFunction", back_populates="framework", cascade="all, delete-orphan", order_by="FrameworkFunction.display_order")


class FrameworkFunction(Base):
    __tablename__ = "framework_functions"

    id = Column(Integer, primary_key=True, index=True)
    framework_id = Column(Integer, ForeignKey("frameworks.id", ondelete="CASCADE"), nullable=False, index=True)
    identifier = Column(String(20), nullable=False, index=True)  # e.g., "GV", "ID", "PR", "DE", "RS", "RC"
    name = Column(String(100), nullable=False)  # e.g., "Govern", "Identify", etc.
    description = Column(Text, nullable=True)
    display_order = Column(Integer, default=0, nullable=False)

    framework = relationship("Framework", back_populates="functions")
    categories = relationship("FrameworkCategory", back_populates="function", cascade="all, delete-orphan", order_by="FrameworkCategory.display_order")


class FrameworkCategory(Base):
    __tablename__ = "framework_categories"

    id = Column(Integer, primary_key=True, index=True)
    function_id = Column(Integer, ForeignKey("framework_functions.id", ondelete="CASCADE"), nullable=False, index=True)
    identifier = Column(String(50), nullable=False, index=True)  # e.g., "GV.OC", "PR.AA"
    name = Column(String(255), nullable=False)  # e.g., "Organizational Context"
    description = Column(Text, nullable=True)
    display_order = Column(Integer, default=0, nullable=False)

    function = relationship("FrameworkFunction", back_populates="categories")
    subcategories = relationship("FrameworkSubcategory", back_populates="category", cascade="all, delete-orphan", order_by="FrameworkSubcategory.display_order")


class FrameworkSubcategory(Base):
    __tablename__ = "framework_subcategories"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("framework_categories.id", ondelete="CASCADE"), nullable=False, index=True)
    identifier = Column(String(50), unique=True, nullable=False, index=True)  # e.g., "GV.OC-01"
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)  # Official NIST CSF outcome statement
    display_order = Column(Integer, default=0, nullable=False)

    category = relationship("FrameworkCategory", back_populates="subcategories")
    organization_controls = relationship("OrganizationControl", back_populates="subcategory", cascade="all, delete-orphan")
    policy_mappings = relationship("PolicyControlMapping", back_populates="subcategory", cascade="all, delete-orphan")