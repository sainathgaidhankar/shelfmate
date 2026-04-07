"""add uploaded images table

Revision ID: 2c1ddf8cf4aa
Revises: 7093265a8bc8
Create Date: 2026-04-07 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "2c1ddf8cf4aa"
down_revision = "7093265a8bc8"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "uploaded_images",
        sa.Column("image_id", sa.String(length=32), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("data", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("image_id"),
    )


def downgrade():
    op.drop_table("uploaded_images")
