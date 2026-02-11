"""empty message

Revision ID: 8bd93b9b1e74
Revises: 
Create Date: 2026-02-11 15:23:26.397508

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8bd93b9b1e74'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Create independent tables first (no foreign keys)
    op.create_table('players',
        sa.Column('localId', sa.Integer(), nullable=False),
        sa.Column('id', sa.Integer(), nullable=True),
        sa.Column('player_name', sa.String(), nullable=False),
        sa.Column('title', sa.Enum('coach', 'defenders', 'keepers', 'midfielders', 'attackers', name='titletype'), nullable=True),
        sa.Column('height', sa.Integer(), nullable=True),
        sa.Column('date_of_birth', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('localId'),
        sa.UniqueConstraint('id')
    )
    op.create_index(op.f('ix_players_localId'), 'players', ['localId'], unique=True)
    
    # 2. Create seasons (no foreign keys)
    op.create_table('seasons',
        sa.Column('local_id', sa.Integer(), nullable=False),
        sa.Column('id', sa.Integer(), nullable=True),
        sa.Column('season_year_string', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('local_id')
    )
    op.create_index(op.f('ix_seasons_local_id'), 'seasons', ['local_id'], unique=False)
    
    # 3. Add columns to leagues (must happen before teams)
    op.add_column('leagues', sa.Column('local_id', sa.Integer(), nullable=False))
    op.add_column('leagues', sa.Column('season_id', sa.Integer(), nullable=False))
    op.alter_column('leagues', 'id',
               existing_type=sa.INTEGER(),
               nullable=True,
               existing_server_default=sa.text("nextval('leagues_id_seq'::regclass)"))
    op.create_foreign_key(None, 'leagues', 'seasons', ['season_id'], ['local_id'])
    
    # 4. NOW create teams (after leagues and seasons exist)
    op.create_table('teams',
        sa.Column('local_id', sa.Integer(), nullable=False),
        sa.Column('id', sa.Integer(), nullable=True),
        sa.Column('season_id', sa.Integer(), nullable=True),
        sa.Column('league_id', sa.Integer(), nullable=True),
        sa.Column('team_name', sa.String(), nullable=False),
        sa.Column('team_logo_url', sa.String(), nullable=True),
        sa.Column('played', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['league_id'], ['leagues.local_id'], ),
        sa.ForeignKeyConstraint(['season_id'], ['seasons.local_id'], ),
        sa.PrimaryKeyConstraint('local_id'),
        sa.UniqueConstraint('team_name')
    )
    op.create_index(op.f('ix_teams_local_id'), 'teams', ['local_id'], unique=False)
    
    # 5. Update fixtures (depends on teams and leagues)
    op.add_column('fixtures', sa.Column('local_id', sa.Integer(), nullable=False))
    op.add_column('fixtures', sa.Column('team_id', sa.Integer(), nullable=False))
    op.alter_column('fixtures', 'match_id',
               existing_type=sa.INTEGER(),
               nullable=True,
               existing_server_default=sa.text("nextval('fixtures_match_id_seq'::regclass)"))
    op.drop_constraint(op.f('fixtures_league_id_fkey'), 'fixtures', type_='foreignkey')
    op.create_foreign_key(None, 'fixtures', 'teams', ['team_id'], ['local_id'])
    op.create_foreign_key(None, 'fixtures', 'leagues', ['league_id'], ['local_id'])
    
    # 6. Rest of the updates
    op.add_column('popular_leagues', sa.Column('local_id', sa.Integer(), nullable=False))
    op.alter_column('popular_leagues', 'id',
               existing_type=sa.INTEGER(),
               nullable=True)
    op.alter_column('stakes', 'public',
               existing_type=sa.BOOLEAN(),
               nullable=True,
               existing_server_default=sa.text('true'))
    op.drop_constraint(op.f('stakes_match_id_fkey'), 'stakes', type_='foreignkey')
    op.create_foreign_key(None, 'stakes', 'fixtures', ['match_id'], ['local_id'])


def downgrade() -> None:
    """Downgrade schema."""
    # Keep the existing downgrade function as is
    op.drop_constraint(None, 'stakes', type_='foreignkey')
    op.create_foreign_key(op.f('stakes_match_id_fkey'), 'stakes', 'fixtures', ['match_id'], ['match_id'])
    op.alter_column('stakes', 'public',
               existing_type=sa.BOOLEAN(),
               nullable=False,
               existing_server_default=sa.text('true'))
    op.alter_column('popular_leagues', 'id',
               existing_type=sa.INTEGER(),
               nullable=False)
    op.drop_column('popular_leagues', 'local_id')
    op.drop_constraint(None, 'leagues', type_='foreignkey')
    op.alter_column('leagues', 'id',
               existing_type=sa.INTEGER(),
               nullable=False,
               existing_server_default=sa.text("nextval('leagues_id_seq'::regclass)"))
    op.drop_column('leagues', 'season_id')
    op.drop_column('leagues', 'local_id')
    op.drop_constraint(None, 'fixtures', type_='foreignkey')
    op.drop_constraint(None, 'fixtures', type_='foreignkey')
    op.create_foreign_key(op.f('fixtures_league_id_fkey'), 'fixtures', 'leagues', ['league_id'], ['id'])
    op.alter_column('fixtures', 'match_id',
               existing_type=sa.INTEGER(),
               nullable=False,
               existing_server_default=sa.text("nextval('fixtures_match_id_seq'::regclass)"))
    op.drop_column('fixtures', 'team_id')
    op.drop_column('fixtures', 'local_id')
    op.drop_index(op.f('ix_teams_local_id'), table_name='teams')
    op.drop_table('teams')
    op.drop_index(op.f('ix_seasons_local_id'), table_name='seasons')
    op.drop_table('seasons')
    op.drop_index(op.f('ix_players_localId'), table_name='players')
    op.drop_table('players')