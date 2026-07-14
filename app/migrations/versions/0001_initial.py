"""initial schema: tokens + spread_opportunities

Revision ID: 0001_initial
Revises:
Create Date: 2023-06-27 19:34:39.426024

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tokens",
        sa.Column("exchange", sa.String(), nullable=False),
        sa.Column("symbol", sa.String(), nullable=False),
        sa.Column("ask", sa.Float(), nullable=True),
        sa.Column("askQ", sa.Float(), nullable=True),
        sa.Column("bid", sa.Float(), nullable=True),
        sa.Column("bidQ", sa.Float(), nullable=True),
        sa.Column("ts", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("exchange", "symbol"),
    )

    op.create_table(
        "spread_opportunities",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("symbol", sa.String(), nullable=True),
        sa.Column("buy_exchange", sa.String(), nullable=True),
        sa.Column("buy_price", sa.Float(), nullable=True),
        sa.Column("sell_exchange", sa.String(), nullable=True),
        sa.Column("sell_price", sa.Float(), nullable=True),
        sa.Column("spread_pct", sa.Float(), nullable=True),
        sa.Column("ts", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_spread_opportunities_symbol"),
        "spread_opportunities",
        ["symbol"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_spread_opportunities_symbol"), table_name="spread_opportunities"
    )
    op.drop_table("spread_opportunities")
    op.drop_table("tokens")
