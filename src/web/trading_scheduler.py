"""
Trading Scheduler Service
Schedules signal generation and trade execution tasks during market hours
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional, Callable
from datetime import datetime, time
import threading
import time as time_module

from src.web.market_hours import get_market_hours_manager, MarketHoursManager

logger = logging.getLogger(__name__)


class TradingScheduler:
    """
    Schedules trading tasks using simple threading-based scheduler.
    Can be replaced with APScheduler for more advanced scheduling.
    """
    
    def __init__(self):
        self.market_hours = get_market_hours_manager()
        self.is_running = False
        self.threads: List[threading.Thread] = []
        self.jobs: Dict[str, Dict] = {}
        self.stop_event = threading.Event()
    
    def start_daily_schedule(self) -> bool:
        """
        Start all scheduled trading tasks.
        
        Returns:
            True if started successfully
        """
        if self.is_running:
            logger.warning("Scheduler is already running")
            return False
        
        self.is_running = True
        self.stop_event.clear()
        
        logger.info("Starting trading scheduler...")
        
        # Schedule pre-market scan (9:00 AM)
        self.register_job(
            name='pre_market_scan',
            func=self._pre_market_scan,
            schedule_time=time(9, 0),
            interval_seconds=None  # Run once daily
        )
        
        # Schedule signal generation (every 5 minutes during market hours)
        self.register_job(
            name='signal_generation',
            func=self._signal_generation_loop,
            schedule_time=None,  # Run immediately
            interval_seconds=300  # 5 minutes
        )
        
        # Schedule trade execution (every 1 minute during market hours)
        self.register_job(
            name='trade_execution',
            func=self._trade_execution_loop,
            schedule_time=None,  # Run immediately
            interval_seconds=60  # 1 minute
        )
        
        # Schedule post-market cleanup (3:45 PM)
        self.register_job(
            name='post_market_cleanup',
            func=self._post_market_cleanup,
            schedule_time=time(15, 45),
            interval_seconds=None  # Run once daily
        )
        
        # Start all job threads
        for job_name, job_info in self.jobs.items():
            thread = threading.Thread(
                target=self._run_job,
                args=(job_name,),
                daemon=True,
                name=f"Scheduler-{job_name}"
            )
            thread.start()
            self.threads.append(thread)
            logger.info(f"Started job thread: {job_name}")
        
        logger.info("Trading scheduler started successfully")
        return True
    
    def stop_schedule(self) -> bool:
        """
        Stop all scheduled tasks.
        
        Returns:
            True if stopped successfully
        """
        if not self.is_running:
            logger.warning("Scheduler is not running")
            return False
        
        logger.info("Stopping trading scheduler...")
        self.is_running = False
        self.stop_event.set()
        
        # Wait for threads to finish (with timeout)
        for thread in self.threads:
            thread.join(timeout=5.0)
        
        self.threads.clear()
        logger.info("Trading scheduler stopped")
        return True
    
    def register_job(
        self,
        name: str,
        func: Callable,
        schedule_time: Optional[time] = None,
        interval_seconds: Optional[int] = None
    ) -> None:
        """
        Register a scheduled job.
        
        Args:
            name: Job name (unique identifier)
            func: Function to execute
            schedule_time: Time of day to run (for daily jobs)
            interval_seconds: Interval in seconds (for recurring jobs)
        """
        self.jobs[name] = {
            'func': func,
            'schedule_time': schedule_time,
            'interval_seconds': interval_seconds,
            'last_run': None
        }
        logger.info(f"Registered job: {name} (time={schedule_time}, interval={interval_seconds}s)")
    
    def _run_job(self, job_name: str) -> None:
        """Run a scheduled job in a loop"""
        if job_name not in self.jobs:
            logger.error(f"Job {job_name} not found")
            return
        
        job_info = self.jobs[job_name]
        func = job_info['func']
        schedule_time = job_info.get('schedule_time')
        interval_seconds = job_info.get('interval_seconds')
        
        logger.info(f"Job thread {job_name} started")
        
        while self.is_running and not self.stop_event.is_set():
            try:
                # Check if it's time to run
                if schedule_time:
                    # Daily scheduled job
                    now = datetime.now()
                    target_time = datetime.combine(now.date(), schedule_time)
                    
                    # If target time has passed today, schedule for tomorrow
                    if now.time() > schedule_time:
                        target_time += time_module.timedelta(days=1)
                    
                    # Wait until target time
                    wait_seconds = (target_time - now).total_seconds()
                    if wait_seconds > 0:
                        if self.stop_event.wait(timeout=wait_seconds):
                            break  # Stop requested
                
                # Check market hours for trading jobs
                if job_name in ['signal_generation', 'trade_execution']:
                    if not self.market_hours.is_market_open():
                        # Wait until market opens
                        next_open = self.market_hours.get_next_market_open()
                        if next_open:
                            next_open_dt = datetime.fromisoformat(next_open)
                            wait_seconds = (next_open_dt - datetime.now()).total_seconds()
                            if wait_seconds > 0:
                                logger.info(f"Market closed. Waiting until {next_open} for {job_name}")
                                if self.stop_event.wait(timeout=min(wait_seconds, 3600)):  # Max 1 hour wait
                                    break
                        else:
                            # No next open time, wait 1 hour and check again
                            if self.stop_event.wait(timeout=3600):
                                break
                            continue
                
                # Execute job
                logger.debug(f"Executing job: {job_name}")
                func()
                job_info['last_run'] = datetime.now()
                
                # Wait for next interval
                if interval_seconds:
                    if self.stop_event.wait(timeout=interval_seconds):
                        break  # Stop requested
                elif schedule_time:
                    # Daily job - wait until next day
                    if self.stop_event.wait(timeout=86400):  # 24 hours
                        break
            
            except Exception as e:
                logger.error(f"Error in job {job_name}: {e}")
                # Wait before retrying
                if self.stop_event.wait(timeout=60):
                    break
        
        logger.info(f"Job thread {job_name} stopped")
    
    def _pre_market_scan(self) -> None:
        """Pre-market scan task (9:00 AM)"""
        logger.info("[Scheduler] Running pre-market scan...")
        # This will be implemented by the caller
        # Placeholder for now
        pass
    
    def _signal_generation_loop(self) -> None:
        """Signal generation task (every 5 minutes during market hours)"""
        logger.debug("[Scheduler] Running signal generation...")
        # This will be implemented by the caller
        # Placeholder for now
        pass
    
    def _trade_execution_loop(self) -> None:
        """Trade execution task (every 1 minute during market hours)"""
        logger.debug("[Scheduler] Running trade execution...")
        # This will be implemented by the caller
        # Placeholder for now
        pass
    
    def _post_market_cleanup(self) -> None:
        """Post-market cleanup task (3:45 PM)"""
        logger.info("[Scheduler] Running post-market cleanup...")
        # This will be implemented by the caller
        # Placeholder for now
        pass
    
    def get_job_status(self, job_name: Optional[str] = None) -> Dict:
        """
        Get status of scheduled jobs.
        
        Args:
            job_name: Specific job name (if None, returns all jobs)
        
        Returns:
            Dictionary with job status
        """
        if job_name:
            if job_name in self.jobs:
                job_info = self.jobs[job_name]
                return {
                    'name': job_name,
                    'last_run': job_info['last_run'].isoformat() if job_info['last_run'] else None,
                    'schedule_time': job_info.get('schedule_time').isoformat() if job_info.get('schedule_time') else None,
                    'interval_seconds': job_info.get('interval_seconds')
                }
            else:
                return {'error': f'Job {job_name} not found'}
        else:
            return {
                'is_running': self.is_running,
                'jobs': {
                    name: {
                        'last_run': info['last_run'].isoformat() if info['last_run'] else None,
                        'schedule_time': info.get('schedule_time').isoformat() if info.get('schedule_time') else None,
                        'interval_seconds': info.get('interval_seconds')
                    }
                    for name, info in self.jobs.items()
                }
            }


# Global instance
_trading_scheduler: Optional[TradingScheduler] = None


def get_trading_scheduler() -> TradingScheduler:
    """Get global trading scheduler instance"""
    global _trading_scheduler
    if _trading_scheduler is None:
        _trading_scheduler = TradingScheduler()
    return _trading_scheduler
