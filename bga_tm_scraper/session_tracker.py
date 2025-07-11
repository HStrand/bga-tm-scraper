"""
Session Statistics Tracker for Terraforming Mars Scraper

Tracks statistics and metrics during a scraping session to provide
comprehensive reporting for email notifications.
"""

from datetime import datetime
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class SessionTracker:
    """Tracks statistics during a scraping session"""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.end_time = None
        self.termination_reason = None
        
        # Session counters
        self.games_processed = 0
        self.successful_scrapes = 0
        self.successful_parses = 0
        self.failed_operations = 0
        self.skipped_games = 0
        
        # Additional tracking
        self.players_processed = 0
        self.new_games_found = 0
        self.already_processed_games = 0
        self.errors = []
        
        logger.info(f"Session tracking started at {self.start_time}")
    
    def increment_games_processed(self):
        """Increment the count of games processed"""
        self.games_processed += 1
    
    def increment_successful_scrapes(self):
        """Increment the count of successful scrapes"""
        self.successful_scrapes += 1
    
    def increment_successful_parses(self):
        """Increment the count of successful parses"""
        self.successful_parses += 1
    
    def increment_failed_operations(self):
        """Increment the count of failed operations"""
        self.failed_operations += 1
    
    def increment_skipped_games(self):
        """Increment the count of skipped games"""
        self.skipped_games += 1
    
    def increment_players_processed(self):
        """Increment the count of players processed"""
        self.players_processed += 1
    
    def increment_new_games_found(self):
        """Increment the count of new games found"""
        self.new_games_found += 1
    
    def increment_already_processed_games(self):
        """Increment the count of already processed games"""
        self.already_processed_games += 1
    
    def add_error(self, error_message: str, context: str = None):
        """Add an error to the tracking"""
        error_entry = {
            'timestamp': datetime.now(),
            'message': error_message,
            'context': context
        }
        self.errors.append(error_entry)
        logger.error(f"Session error recorded: {error_message} (Context: {context})")
    
    def set_termination_reason(self, reason: str):
        """Set the reason for session termination"""
        self.termination_reason = reason
        logger.info(f"Session termination reason set: {reason}")
    
    def end_session(self, termination_reason: str = None):
        """Mark the session as ended"""
        self.end_time = datetime.now()
        if termination_reason:
            self.termination_reason = termination_reason
        
        duration = self.end_time - self.start_time
        logger.info(f"Session ended at {self.end_time} (Duration: {duration})")
        logger.info(f"Session summary: {self.games_processed} games processed, "
                   f"{self.successful_scrapes} scraped, {self.successful_parses} parsed")
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get comprehensive session statistics"""
        current_time = self.end_time or datetime.now()
        duration = current_time - self.start_time
        
        return {
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration': duration,
            'duration_seconds': duration.total_seconds(),
            'termination_reason': self.termination_reason or "Unknown",
            
            # Core metrics
            'games_processed': self.games_processed,
            'successful_scrapes': self.successful_scrapes,
            'successful_parses': self.successful_parses,
            'failed_operations': self.failed_operations,
            'skipped_games': self.skipped_games,
            
            # Additional metrics
            'players_processed': self.players_processed,
            'new_games_found': self.new_games_found,
            'already_processed_games': self.already_processed_games,
            'total_errors': len(self.errors),
            'errors': self.errors,
            
            # Calculated metrics
            'scrape_success_rate': (self.successful_scrapes / max(1, self.games_processed)) * 100,
            'parse_success_rate': (self.successful_parses / max(1, self.successful_scrapes)) * 100,
            'overall_success_rate': (self.successful_parses / max(1, self.games_processed)) * 100,
        }
    
    def get_summary_string(self) -> str:
        """Get a brief summary string for logging"""
        stats = self.get_session_stats()
        return (f"Session Summary: {stats['games_processed']} games processed, "
                f"{stats['successful_scrapes']} scraped ({stats['scrape_success_rate']:.1f}%), "
                f"{stats['successful_parses']} parsed ({stats['parse_success_rate']:.1f}%), "
                f"{stats['failed_operations']} failed, {stats['skipped_games']} skipped")
    
    def log_progress(self, interval: int = 10):
        """Log progress if games_processed is a multiple of interval"""
        if self.games_processed > 0 and self.games_processed % interval == 0:
            logger.info(f"Progress update: {self.get_summary_string()}")
    
    def record_game_outcome(self, outcome: str, details: str = None):
        """
        Record the outcome of processing a single game
        
        Args:
            outcome: One of 'scraped', 'parsed', 'failed', 'skipped', 'already_processed'
            details: Additional details about the outcome
        """
        self.increment_games_processed()
        
        if outcome == 'scraped':
            self.increment_successful_scrapes()
        elif outcome == 'parsed':
            self.increment_successful_parses()
        elif outcome == 'failed':
            self.increment_failed_operations()
            if details:
                self.add_error(f"Game processing failed: {details}")
        elif outcome == 'skipped':
            self.increment_skipped_games()
        elif outcome == 'already_processed':
            self.increment_already_processed_games()
        
        # Log progress periodically
        self.log_progress()
    
    def is_session_active(self) -> bool:
        """Check if the session is still active (not ended)"""
        return self.end_time is None
    
    def get_runtime_duration(self) -> str:
        """Get formatted runtime duration"""
        current_time = self.end_time or datetime.now()
        duration = current_time - self.start_time
        return str(duration).split('.')[0]  # Remove microseconds


# Global session tracker instance
_session_tracker: Optional[SessionTracker] = None


def get_session_tracker() -> SessionTracker:
    """Get the global session tracker instance"""
    global _session_tracker
    if _session_tracker is None:
        _session_tracker = SessionTracker()
    return _session_tracker


def start_new_session() -> SessionTracker:
    """Start a new session, replacing any existing one"""
    global _session_tracker
    _session_tracker = SessionTracker()
    return _session_tracker


def end_current_session(termination_reason: str = None) -> Optional[SessionTracker]:
    """End the current session and return it"""
    global _session_tracker
    if _session_tracker is not None:
        _session_tracker.end_session(termination_reason)
        return _session_tracker
    return None


def reset_session_tracker():
    """Reset the global session tracker"""
    global _session_tracker
    _session_tracker = None
