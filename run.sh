#!/bin/bash
RED=$(tput setaf 1)
GREEN=$(tput setaf 2)
YELLOW=$(tput setaf 3)
NC=$(tput sgr0) 

check_port() {
    port=$1
    if command -v nc >/dev/null 2>&1; then
        nc -z localhost $port 2>/dev/null
        return $?
    elif command -v curl >/dev/null 2>&1; then
        curl -s telnet://localhost:$port >/dev/null 2>&1
        return $?
    elif command -v bash >/dev/null 2>&1; then
        (echo > /dev/tcp/localhost/$port) >/dev/null 2>&1
        return $?
    else        
        python -c "import socket; s=socket.socket(); s.connect(('localhost',$port))" >/dev/null 2>&1
        return $?
    fi
}

kill_existing_processes() {
    echo "${YELLOW}Checking for existing processes on required ports...${NC}"
    if command -v lsof >/dev/null 2>&1; then
        echo "${YELLOW}Using lsof to find processes${NC}"
        if lsof -i:8000 >/dev/null 2>&1; then
            echo "${YELLOW}Killing process on port 8000 (Django)${NC}"
            kill $(lsof -t -i:8000) 2>/dev/null || true
        fi
        if lsof -i:5000 >/dev/null 2>&1; then
            echo "${YELLOW}Killing process on port 5000 (LibreTranslate)${NC}"
            kill $(lsof -t -i:5000) 2>/dev/null || true
        fi
        if lsof -i:6380 >/dev/null 2>&1; then
            echo "${YELLOW}Killing process on port 6380 (Redis)${NC}"
            kill $(lsof -t -i:6380) 2>/dev/null || true
        fi
    elif command -v netstat >/dev/null 2>&1; then
        echo "${YELLOW}Using netstat to find processes${NC}"
        DJANGO_PID=$(netstat -ano | grep "LISTEN" | grep ":8000" | awk '{print $NF}')
        if [ ! -z "$DJANGO_PID" ]; then
            echo "${YELLOW}Killing process on port 8000 (Django) with PID $DJANGO_PID${NC}"
            kill $DJANGO_PID 2>/dev/null || true
        fi
        LT_PID=$(netstat -ano | grep "LISTEN" | grep ":5000" | awk '{print $NF}')
        if [ ! -z "$LT_PID" ]; then
            echo "${YELLOW}Killing process on port 5000 (LibreTranslate) with PID $LT_PID${NC}"
            kill $LT_PID 2>/dev/null || true
        fi
        REDIS_PID=$(netstat -ano | grep "LISTEN" | grep ":6380" | awk '{print $NF}')
        if [ ! -z "$REDIS_PID" ]; then
            echo "${YELLOW}Killing process on port 6380 (Redis) with PID $REDIS_PID${NC}"
            kill $REDIS_PID 2>/dev/null || true
        fi
    else
        echo "${RED}Could not find tools to detect processes. Using generic approach.${NC}"
    fi
    echo "${YELLOW}Killing processes by name...${NC}"
    if ps aux | grep -i "[c]elery" >/dev/null; then
        echo "${YELLOW}Killing Celery processes${NC}"
        pkill -f "celery" >/dev/null 2>&1 || true
    fi
    if ps aux | grep -i "[l]ibretranslate" >/dev/null; then
        echo "${YELLOW}Killing LibreTranslate processes${NC}"
        pkill -f "libretranslate" >/dev/null 2>&1 || true
    fi    
    if ps aux | grep -i "[r]unserver" >/dev/null; then
        echo "${YELLOW}Killing Django processes${NC}"
        pkill -f "runserver" >/dev/null 2>&1 || true
    fi  
    if ps aux | grep -i "[r]edis-server" >/dev/null; then
        echo "${YELLOW}Killing Redis server processes${NC}"
        pkill -f "redis-server" >/dev/null 2>&1 || true
    fi
    echo "${YELLOW}Waiting for processes to terminate...${NC}"
    sleep 3
}

check_services() {
    echo "${YELLOW}Checking required services...${NC}"    
    if ! check_port 6380; then
        echo "${RED}Redis not running on port 6380${NC}"
        start_redis
    else
        echo "${GREEN}✓ Redis already running${NC}"
    fi
    if ! check_port 5000; then
        echo "${RED}LibreTranslate not running on port 5000${NC}"
        start_libretranslate
    else
        echo "${GREEN}✓ LibreTranslate already running${NC}"
    fi
}

start_redis() {
    echo "${YELLOW}Starting Redis server...${NC}"
    redis-server NewsAggregator/redis.conf &
    REDIS_PID=$!
    echo "${GREEN}Redis started with PID $REDIS_PID${NC}"
    sleep 3
}

start_libretranslate() {
    echo "${YELLOW}Starting LibreTranslate server...${NC}"
    libretranslate --host localhost --port 5000 --load-only en,es,fr,de,it,ru --metrics &
    LT_PID=$!
    echo "${GREEN}LibreTranslate started with PID $LT_PID${NC}"
    sleep 5
}

start_django() {
    echo "${YELLOW}Starting Django server...${NC}"
    python NewsAggregator/manage.py migrate
    python NewsAggregator/manage.py runserver &
    DJANGO_PID=$!
    echo "${GREEN}Django started with PID $DJANGO_PID${NC}"
    sleep 3
}

start_celery() {
    echo "${YELLOW}Starting Celery workers...${NC}"
    cd NewsAggregator
    
    # Start Celery beat
    celery -A NewsAggregator beat -l info &
    BEAT_PID=$!
    echo "${GREEN}Celery beat started with PID $BEAT_PID${NC}"
    
    # Start worker with GPU support and spawn method
    export PYTHONPATH=$PYTHONPATH:$(pwd)
    export CELERY_WORKER_ID=0
    celery -A NewsAggregator worker -l info -Q celery,translations --concurrency=1 --pool=prefork --prefetch-multiplier=1 &
    WORKER_PID=$!
    echo "${GREEN}Celery worker started with PID $WORKER_PID${NC}"
    
    cd ..
    sleep 3
}

trigger_initial_tasks() {
    echo "${YELLOW}Triggering initial tasks...${NC}"
    cd NewsAggregator
    python manage.py shell -c "
import multiprocessing
multiprocessing.set_start_method('spawn', force=True)
from core.tasks import scrape_articles, update_event_clusters, update_tfidf_matrix, update_faiss_index
scrape_articles.delay()
update_event_clusters.delay()
update_tfidf_matrix.delay()
update_faiss_index.delay()
"
    cd ..
    echo "${GREEN}Initial tasks triggered${NC}"
}

check_venv() {
    if [ -d "../jayanth-ml" ]; then
        echo "${YELLOW}Activating virtual environment...${NC}"
        source ../jayanth-ml/bin/activate
    else
        echo "${RED}Virtual environment not found in '../jayanth-ml' directory${NC}"
        exit 1
    fi
}

main() {
    check_venv
    kill_existing_processes
    check_services
    start_django
    start_celery
    trigger_initial_tasks
    echo "\n${GREEN}All services started!${NC}"
    echo "----------------------------------------"
    echo "Access URLs:"
    echo "Django admin:      http://localhost:8000/admin"
    echo "User dashboard:    http://localhost:8000"
    echo "Celery flower:     http://localhost:5555"
    echo "LibreTranslate:    http://localhost:5000"
    echo "\n${YELLOW}Press Ctrl+C to stop all services${NC}"
    trap 'pkill -P $$' SIGINT SIGTERM
    wait
}

main