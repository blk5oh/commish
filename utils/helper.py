import pytz
from datetime import datetime, timedelta

def check_availability():
    est = pytz.timezone('US/Eastern')
    now_est = datetime.now(est)
    current_hour = now_est.hour
    current_day = now_est.weekday()

    if current_day == 1 and current_hour >= 4:  # Tuesday 4am onwards
        return True, now_est.strftime("%A")
    elif 1 < current_day < 4:  # All day Wednesday and Thursday until 7pm
        return True, now_est.strftime("%A")
    elif current_day == 4 and current_hour < 19:  # Thursday until 7pm
        return True, now_est.strftime("%A")
    else:
        return False, now_est.strftime("%A")

def get_nfl_season_year(current_date):
    """
    Determines the NFL season year based on the current date.
    """
    if current_date.month >= 9:  # September or later = current year's season
        return current_date.year
    else:  # January through August = previous year's season
        return current_date.year - 1

def get_nfl_week_1_start(season_year):
    """
    Calculates the start of NFL Week 1 for a given season.
    Uses the first Thursday of September as approximation.
    """
    first_of_sept = datetime(season_year, 9, 1)
    
    # Find first Thursday (weekday 3)
    days_until_thursday = (3 - first_of_sept.weekday()) % 7
    if days_until_thursday == 0 and first_of_sept.weekday() != 3:
        days_until_thursday = 7
    
    first_thursday = first_of_sept + timedelta(days=days_until_thursday)
    
    # Use the preceding Wednesday as the "start" of Week 1 for scoring purposes
    week_1_start = first_thursday - timedelta(days=1)
    
    return week_1_start

def generate_nfl_schedule(season_year):
    """
    Generates the complete NFL schedule for a given season.
    """
    week_1_start = get_nfl_week_1_start(season_year)
    
    schedule = {}
    current_date = week_1_start
    
    # Regular season: Weeks 1-18
    for week in range(1, 19):
        schedule[current_date] = week
        current_date += timedelta(days=7)
    
    return schedule

def get_current_week(current_date):
    """
    Determines what NFL week we're currently in (not necessarily completed).
    """
    season_year = get_nfl_season_year(current_date)
    schedule = generate_nfl_schedule(season_year)
    
    sorted_dates = sorted(schedule.keys(), reverse=True)
    
    for week_start_date in sorted_dates:
        if current_date >= week_start_date:
            return schedule[week_start_date]
    
    return 1

def get_last_completed_week(current_date):
    """
    Gets the most recent week that is DEFINITELY completed with finalized scoring.
    Very conservative approach - only returns a week if we're certain it's done.
    """
    est = pytz.timezone('US/Eastern')
    current_est = current_date.astimezone(est) if current_date.tzinfo else est.localize(current_date)
    
    current_week = get_current_week(current_date)
    
    # NFL games typically:
    # - Thursday Night Football (week starts)
    # - Sunday games
    # - Monday Night Football (week ends)
    # - Scores finalized by Tuesday 6 AM EST
    
    # Only consider a week "completed" if we're at least Tuesday 6 AM after it ended
    # This means we need to be in the following week AND it's Tuesday 6 AM or later
    
    # If we're in Week N, then Week N-1 is completed only if:
    # 1. It's Tuesday 6 AM or later in Week N, OR
    # 2. It's Wednesday or later in Week N
    
    if current_est.weekday() >= 2:  # Wednesday or later
        # Definitely safe to use previous week
        return max(1, current_week - 1)
    elif current_est.weekday() == 1 and current_est.hour >= 6:  # Tuesday 6 AM or later
        # Should be safe to use previous week
        return max(1, current_week - 1)
    else:
        # Monday or early Tuesday - be extra conservative
        # Use the week before the previous week to be absolutely sure
        return max(1, current_week - 2)

def get_available_weeks_for_recap(current_date):
    """
    Returns a list of weeks that definitely have completed, finalized scoring.
    Most conservative approach.
    """
    last_completed = get_last_completed_week(current_date)
    
    if last_completed < 1:
        return []
    
    # Return all weeks from 1 up to the last completed week
    return list(range(1, last_completed + 1))

def get_safest_week_for_recap(current_date):
    """
    Returns the safest week to use for recap generation.
    Guarantees the week has completed scoring.
    """
    available_weeks = get_available_weeks_for_recap(current_date)
    
    if not available_weeks:
        return 1  # Fallback to Week 1 if nothing is available
    
    # Return the most recent completed week
    return available_weeks[-1]

# For debugging - shows what week would be selected
def debug_week_selection(current_date):
    """
    Debug function to show week selection logic.
    """
    current_week = get_current_week(current_date)
    completed_week = get_last_completed_week(current_date)
    safest_week = get_safest_week_for_recap(current_date)
    available_weeks = get_available_weeks_for_recap(current_date)
    
    est = pytz.timezone('US/Eastern')
    current_est = current_date.astimezone(est) if current_date.tzinfo else est.localize(current_date)
    
    return {
        'current_date': current_est.strftime('%Y-%m-%d %H:%M %Z'),
        'current_week': current_week,
        'last_completed_week': completed_week,
        'safest_week_for_recap': safest_week,
        'available_weeks': available_weeks,
        'day_of_week': current_est.strftime('%A'),
        'reasoning': f"Using week {safest_week} because it's guaranteed to have final scores"
    }
