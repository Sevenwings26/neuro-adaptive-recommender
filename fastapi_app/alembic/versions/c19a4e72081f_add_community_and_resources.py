"""add_community_and_resources

Revision ID: c19a4e72081f
Revises: bd562ff6c33f
Create Date: 2026-09-15 16:50:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c19a4e72081f'
down_revision: Union[str, Sequence[str], None] = 'bd562ff6c33f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. community_circles
    op.create_table(
        'community_circles',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('slug', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('icon', sa.String(length=20), nullable=False),
        sa.Column('order_num', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_community_circles_id'), 'community_circles', ['id'], unique=False)
    op.create_index(op.f('ix_community_circles_slug'), 'community_circles', ['slug'], unique=True)

    # 2. community_posts
    op.create_table(
        'community_posts',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('circle_id', sa.Uuid(), nullable=False),
        sa.Column('author_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('post_type', sa.String(length=50), nullable=False, server_default='question'),
        sa.Column('is_anonymous', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('author_flair', sa.String(length=100), nullable=True),
        sa.Column('location_city', sa.String(length=100), nullable=True),
        sa.Column('location_state', sa.String(length=100), nullable=True),
        sa.Column('views_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_pinned', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['circle_id'], ['community_circles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_community_posts_id'), 'community_posts', ['id'], unique=False)
    op.create_index(op.f('ix_community_posts_author_id'), 'community_posts', ['author_id'], unique=False)
    op.create_index(op.f('ix_community_posts_circle_id'), 'community_posts', ['circle_id'], unique=False)
    op.create_index(op.f('ix_community_posts_created_at'), 'community_posts', ['created_at'], unique=False)

    # 3. community_replies
    op.create_table(
        'community_replies',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('post_id', sa.Uuid(), nullable=False),
        sa.Column('author_id', sa.Integer(), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('is_anonymous', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('author_flair', sa.String(length=100), nullable=True),
        sa.Column('is_clinician_endorsed', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('endorsed_by_clinician_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['endorsed_by_clinician_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['post_id'], ['community_posts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_community_replies_id'), 'community_replies', ['id'], unique=False)
    op.create_index(op.f('ix_community_replies_author_id'), 'community_replies', ['author_id'], unique=False)
    op.create_index(op.f('ix_community_replies_post_id'), 'community_replies', ['post_id'], unique=False)
    op.create_index(op.f('ix_community_replies_created_at'), 'community_replies', ['created_at'], unique=False)

    # 4. community_reactions
    op.create_table(
        'community_reactions',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('post_id', sa.Uuid(), nullable=True),
        sa.Column('reply_id', sa.Uuid(), nullable=True),
        sa.Column('reaction_type', sa.String(length=30), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['post_id'], ['community_posts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reply_id'], ['community_replies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'post_id', 'reaction_type', name='uq_user_post_reaction'),
        sa.UniqueConstraint('user_id', 'reply_id', 'reaction_type', name='uq_user_reply_reaction')
    )
    op.create_index(op.f('ix_community_reactions_id'), 'community_reactions', ['id'], unique=False)
    op.create_index(op.f('ix_community_reactions_user_id'), 'community_reactions', ['user_id'], unique=False)
    op.create_index(op.f('ix_community_reactions_post_id'), 'community_reactions', ['post_id'], unique=False)
    op.create_index(op.f('ix_community_reactions_reply_id'), 'community_reactions', ['reply_id'], unique=False)

    # 5. local_resources
    op.create_table(
        'local_resources',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('submitted_by_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('city', sa.String(length=100), nullable=False),
        sa.Column('state', sa.String(length=50), nullable=False),
        sa.Column('address_or_url', sa.String(length=255), nullable=True),
        sa.Column('contact_info', sa.String(length=100), nullable=True),
        sa.Column('upvotes_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['submitted_by_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_local_resources_id'), 'local_resources', ['id'], unique=False)
    op.create_index(op.f('ix_local_resources_city'), 'local_resources', ['city'], unique=False)
    op.create_index(op.f('ix_local_resources_state'), 'local_resources', ['state'], unique=False)
    op.create_index(op.f('ix_local_resources_created_at'), 'local_resources', ['created_at'], unique=False)

    # 6. local_resource_votes
    op.create_table(
        'local_resource_votes',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('resource_id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['resource_id'], ['local_resources.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'resource_id', name='uq_user_resource_vote')
    )
    op.create_index(op.f('ix_local_resource_votes_id'), 'local_resource_votes', ['id'], unique=False)
    op.create_index(op.f('ix_local_resource_votes_user_id'), 'local_resource_votes', ['user_id'], unique=False)
    op.create_index(op.f('ix_local_resource_votes_resource_id'), 'local_resource_votes', ['resource_id'], unique=False)


def downgrade() -> None:
    op.drop_table('local_resource_votes')
    op.drop_table('local_resources')
    op.drop_table('community_reactions')
    op.drop_table('community_replies')
    op.drop_table('community_posts')
    op.drop_table('community_circles')
