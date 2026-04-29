# app/database/models.py

from sqlalchemy import (
    Column, Integer, String, Float, Boolean,
    Date, DateTime, Numeric, Text, ForeignKey,
    CheckConstraint, Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.db import Base


class Category(Base):
    __tablename__ = "categories"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    name       = Column(String(100), unique=True, nullable=False)
    color_hex  = Column(String(7), default="#888888")
    created_at = Column(DateTime, server_default=func.now())

    transactions = relationship("Transaction", backref="category", lazy="dynamic")
    forecasts    = relationship("Forecast",    backref="category", lazy="dynamic")

    def __repr__(self):
        return f"<Category id={self.id} name='{self.name}'>"

    def to_dict(self):
        return {
            "id":        self.id,
            "name":      self.name,
            "color_hex": self.color_hex,
        }


class Transaction(Base):
    __tablename__ = "transactions"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    date        = Column(Date, nullable=False)
    description = Column(Text, nullable=False)
    amount      = Column(Numeric(12, 2), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    is_anomaly  = Column(Boolean, default=False)
    confidence  = Column(Float, nullable=True)
    raw_text    = Column(Text, nullable=True)
    uploaded_at = Column(DateTime, server_default=func.now())

    anomaly = relationship("Anomaly", back_populates="transaction", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_transactions_date",     "date"),
        Index("idx_transactions_category", "category_id"),
        Index("idx_transactions_anomaly",  "is_anomaly"),
    )

    def __repr__(self):
        return (
            f"<Transaction id={self.id} "
            f"date={self.date} "
            f"amount={self.amount} "
            f"desc='{str(self.description)[:25]}...'>"
        )

    def to_dict(self):
        return {
            "id":             self.id,
            "date":           str(self.date),
            "description":    self.description,
            "amount":         float(self.amount),
            "category":       self.category.name if self.category else "Uncategorized",
            "category_color": self.category.color_hex if self.category else "#888888",
            "is_anomaly":     self.is_anomaly,
            "confidence":     round(self.confidence, 2) if self.confidence else None,
            "uploaded_at":    str(self.uploaded_at),
        }


class Anomaly(Base):
    __tablename__ = "anomalies"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, unique=True)
    reason         = Column(Text)
    severity       = Column(String(20))
    detected_at    = Column(DateTime, server_default=func.now())

    __table_args__ = (
        CheckConstraint(
            "severity IN ('low', 'medium', 'high')",
            name="chk_severity_values"
        ),
    )

    transaction = relationship("Transaction", back_populates="anomaly")

    def __repr__(self):
        return f"<Anomaly id={self.id} txn_id={self.transaction_id} severity='{self.severity}'>"

    def to_dict(self):
        return {
            "id":             self.id,
            "transaction_id": self.transaction_id,
            "reason":         self.reason,
            "severity":       self.severity,
            "detected_at":    str(self.detected_at),
        }


class Forecast(Base):
    __tablename__ = "forecasts"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    category_id      = Column(Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=False)
    forecast_month   = Column(Date, nullable=False)
    predicted_amount = Column(Numeric(12, 2))
    actual_amount    = Column(Numeric(12, 2), nullable=True)
    created_at       = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("uq_forecast_category_month", "category_id", "forecast_month", unique=True),
    )

    def __repr__(self):
        return (
            f"<Forecast id={self.id} "
            f"category_id={self.category_id} "
            f"month={self.forecast_month} "
            f"predicted={self.predicted_amount}>"
        )

    def to_dict(self):
        return {
            "id":               self.id,
            "category_id":      self.category_id,
            "category":         self.category.name if self.category else "Unknown",
            "forecast_month":   str(self.forecast_month),
            "predicted_amount": float(self.predicted_amount) if self.predicted_amount else 0,
            "actual_amount":    float(self.actual_amount) if self.actual_amount else None,
        }