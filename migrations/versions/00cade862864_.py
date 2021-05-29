"""empty message

Revision ID: 00cade862864
Revises: c8b7e9772a0e
Create Date: 2021-05-04 00:30:32.011321

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '00cade862864'
down_revision = 'c8b7e9772a0e'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('avatar_hash', sa.String(length=32), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('users', 'avatar_hash')
    # ### end Alembic commands ###
