import os
import multiprocessing
import torch

# Set multiprocessing start method to spawn
if __name__ == '__main__':
    multiprocessing.set_start_method('spawn', force=True)

# Celery configuration
broker_url = 'redis://localhost:6380/0'
result_backend = 'redis://localhost:6380/0'
task_serializer = 'json'
result_serializer = 'json'
accept_content = ['json']
timezone = 'UTC'
enable_utc = True

# Worker settings
worker_prefetch_multiplier = 1
worker_max_tasks_per_child = 1
worker_pool = 'prefork'

# CUDA settings
if torch.cuda.is_available():
    os.environ['CUDA_VISIBLE_DEVICES'] = '0' 