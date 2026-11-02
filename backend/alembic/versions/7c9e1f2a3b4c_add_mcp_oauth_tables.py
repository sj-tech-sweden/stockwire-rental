"""add mcp oauth tables

Creates the tables backing the MCP OAuth authorization server: registered
clients, single-use authorization codes, and refresh tokens.

Revision ID: 7c9e1f2a3b4c
Revises: 0106
Create Date: 2026-11-02
"""

revision = '7c9e1f2a3b4c'
down_revision = '0106'
branch_labels = None
depends_on = None

import sqlalchemy as sa

from alembic import op


def upgrade() -> None:
    op.create_table(
        'mcp_oauth_clients',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('client_id', sa.String(length=64), nullable=False),
        sa.Column('client_secret_hash', sa.String(length=255), nullable=True),
        sa.Column('client_name', sa.String(length=255), nullable=False),
        sa.Column('redirect_uris', sa.Text(), nullable=False),
        sa.Column('token_endpoint_auth_method', sa.String(length=32), nullable=False, server_default='none'),
        sa.Column('scope', sa.String(length=255), nullable=False, server_default='mcp'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_mcp_oauth_clients_client_id', 'mcp_oauth_clients', ['client_id'], unique=True)

    op.create_table(
        'mcp_oauth_codes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=64), nullable=False),
        sa.Column('client_id', sa.String(length=64), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('code_challenge', sa.String(length=128), nullable=False),
        sa.Column('redirect_uri', sa.Text(), nullable=False),
        sa.Column('scopes', sa.String(length=255), nullable=False, server_default='mcp'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_mcp_oauth_codes_code', 'mcp_oauth_codes', ['code'], unique=True)
    op.create_index('ix_mcp_oauth_codes_client_id', 'mcp_oauth_codes', ['client_id'])

    op.create_table(
        'mcp_oauth_refresh_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('client_id', sa.String(length=64), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('scopes', sa.String(length=255), nullable=False, server_default='mcp'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_mcp_oauth_refresh_tokens_token_hash', 'mcp_oauth_refresh_tokens', ['token_hash'], unique=True)
    op.create_index('ix_mcp_oauth_refresh_tokens_client_id', 'mcp_oauth_refresh_tokens', ['client_id'])


def downgrade() -> None:
    op.drop_index('ix_mcp_oauth_refresh_tokens_client_id', table_name='mcp_oauth_refresh_tokens')
    op.drop_index('ix_mcp_oauth_refresh_tokens_token_hash', table_name='mcp_oauth_refresh_tokens')
    op.drop_table('mcp_oauth_refresh_tokens')

    op.drop_index('ix_mcp_oauth_codes_client_id', table_name='mcp_oauth_codes')
    op.drop_index('ix_mcp_oauth_codes_code', table_name='mcp_oauth_codes')
    op.drop_table('mcp_oauth_codes')

    op.drop_index('ix_mcp_oauth_clients_client_id', table_name='mcp_oauth_clients')
    op.drop_table('mcp_oauth_clients')
