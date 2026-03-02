"""Vulture whitelist — items listed here are not reported as unused.

Vulture can't detect usage by frameworks (FastAPI routes, Pydantic fields,
SQLAlchemy columns, etc.), so we whitelist those patterns here.

Run: vulture src/ vulture_whitelist.py --min-confidence 80
"""

# ---------------------------------------------------------------------------
# FastAPI router handlers (called by framework, not directly)
# ---------------------------------------------------------------------------
# roms.py
list_roms  # noqa
get_game_detail  # noqa
get_game_states  # noqa
sync_single_game  # noqa
resync_with_igdb_id  # noqa
search_igdb  # noqa
import_roms  # noqa
scan_roms  # noqa
sync_all_roms  # noqa
sync_status  # noqa
sync_thumbnails  # noqa

# runs.py
create_run  # noqa
list_runs  # noqa
get_run_details  # noqa
update_run  # noqa
delete_run  # noqa
resume_run  # noqa
stop_run  # noqa
get_run_metrics  # noqa
list_run_recordings  # noqa
get_run_recording  # noqa

# config.py
get_config  # noqa
update_config  # noqa

# agents.py
create_agent  # noqa
list_agents  # noqa
get_agent  # noqa
delete_agent  # noqa

# play.py
start_play_session  # noqa
stop_play_session  # noqa
play_status  # noqa

# integration.py
launch_integration  # noqa
integration_status  # noqa
stop_integration  # noqa
rescan_integrations  # noqa

# thumbnails.py
get_thumbnail  # noqa

# metadata.py
lifespan  # noqa

# ---------------------------------------------------------------------------
# Pydantic BaseModel field names (accessed by serialization framework)
# ---------------------------------------------------------------------------
# These are accessed dynamically by Pydantic — vulture sees them as unused.
rom_id  # noqa
connector_id  # noqa
connector_name  # noqa
display_name  # noqa
game_id  # noqa
file_path  # noqa
sync_status  # noqa
sync_error  # noqa
synced_at  # noqa
igdb_id  # noqa
igdb_name  # noqa
thumbnail_url  # noqa
thumbnail_status  # noqa
thumbnail_path  # noqa
cover_url  # noqa
screenshot_urls  # noqa
rating_count  # noqa
release_date  # noqa
game_modes  # noqa
player_perspectives  # noqa
learning_rate  # noqa
n_steps  # noqa
batch_size  # noqa
n_epochs  # noqa
gamma  # noqa
gae_lambda  # noqa
clip_range  # noqa
ent_coef  # noqa
vf_coef  # noqa
max_grad_norm  # noqa
normalize_advantage  # noqa
observation_type  # noqa
action_space  # noqa
reward_shaping  # noqa
checkpoint_interval  # noqa
opponent_agent_id  # noqa
opponent_agent_name  # noqa
agent_name  # noqa
game_name  # noqa
game_thumbnail_url  # noqa
latest_step  # noqa
best_reward  # noqa
avg_reward  # noqa
max_steps  # noqa
n_envs  # noqa
total_runs  # noqa
total_steps  # noqa
has_rom  # noqa
has_connector  # noqa
record_bk2  # noqa
frame_skip  # noqa
sticky_action_prob  # noqa
grayscale  # noqa
resize_shape  # noqa
stack_frames  # noqa
default_device  # noqa
roms_directory  # noqa
import_path  # noqa
from_attributes  # noqa
target_update_interval  # noqa
buffer_size  # noqa
exploration_fraction  # noqa
exploration_final_eps  # noqa

# ---------------------------------------------------------------------------
# SQLAlchemy columns & relationships (accessed by ORM)
# ---------------------------------------------------------------------------
created_at  # noqa
updated_at  # noqa
completed_at  # noqa
started_at  # noqa
game_metadata  # noqa
rom  # noqa

# ---------------------------------------------------------------------------
# Enum values
# ---------------------------------------------------------------------------
# RunStatus
PENDING  # noqa
RUNNING  # noqa
COMPLETED  # noqa
FAILED  # noqa
STOPPED  # noqa
PAUSED  # noqa

# Algorithm
PPO  # noqa
DQN  # noqa

# Device
auto  # noqa
cpu  # noqa
cuda  # noqa

# ObservationType / ActionSpace / RewardShaping
image  # noqa
ram  # noqa
filtered  # noqa
multi_discrete  # noqa
all  # noqa
delta  # noqa
custom  # noqa

# ---------------------------------------------------------------------------
# Script entry points & other framework-invoked
# ---------------------------------------------------------------------------
migrate_states_to_dicts  # noqa
