import pytz
from datetime import datetime, timedelta

def check_availability():
    est = pytz.timezone('US/Eastern')
    now_est = datetime.now(est)
    current_hour = now_est.hour
    current_day = now_est.weekday()

    # Availability window is from Tuesday 4am EST to Thursday 7pm EST
    if current_day == 1 and current_hour >= 4:  # Tuesday 4am onwards
        return True, now_est.strftime("%A")
    elif current_day == 2:  # All day Wednesday
        return True, now_est.strftime("%A")
    elif current_day == 3 and current_hour < 19: # Thursday until 7pm EST
        return True, now_est.strftime("%A")
    else:
        return False, now_est.strftime("%A")

def get_nfl_season_year(current_date):
    """
    Determines the NFL season year based on the current date.
    """
    if current_date.month >= 9:  # September or later is the current year's season
        return current_date.year
    else:  # Before September is the previous year's season
        return current_date.year - 1

def get_nfl_week_1_start(season_year):
    """
    Calculates the fantasy start of NFL Week 1 (the Tuesday of the week of the first game).
    """
    first_of_sept = datetime(season_year, 9, 1)
    # Find the first Thursday of September
    days_until_thursday = (3 - first_of_sept.weekday() + 7) % 7
    first_thursday = first_of_sept + timedelta(days=days_until_thursday)
    
    # --- FIX: The start of the fantasy week is the Tuesday before the first Thursday game ---
    # Tuesday is weekday 1.
    days_from_thursday_to_tuesday = first_thursday.weekday() - 1
    week_1_start_date = first_thursday - timedelta(days=days_from_thursday_to_tuesday)
    
    return week_1_start_date

def get_current_week(current_date):
    """
    Calculates the current NFL fantasy week based on the season start date.
    """
    season_year = get_nfl_season_year(current_date)
    week_1_start = get_nfl_week_1_start(season_year)
    
    # Calculate the number of days that have passed since the start of Week 1
    days_since_week_1 = (current_date.replace(tzinfo=None) - week_1_start).days
    
    # Calculate the current week (1-indexed)
    current_week = (days_since_week_1 // 7) + 1
    
    return max(1, current_week)

def get_last_completed_week(current_date):
    """
    Determines the most recently completed week based on the current date.
    A week is considered "complete" after Monday Night Football, so on Tuesday.
    """
    current_week = get_current_week(current_date)
    # Tuesday (weekday 1) is the start of the new fantasy week.
    # Therefore, if it's Tuesday or later, the "current week" has begun,
    # and the "last completed week" is the week before.
    if current_date.weekday() >= 1: # 1 is Tuesday
        return current_week - 1
    else: # If it's Sunday or Monday, we are still in the current week.
        return current_week - 2

def get_available_weeks_for_recap(current_date):
    """
    Gets a list of all fully completed weeks available for a recap.
    """
    last_completed = get_last_completed_week(current_date)
    if last_completed < 1:
        return []
    
    return list(range(1, last_completed + 1))

def get_safest_week_for_recap(current_date):
    """
    Returns the most recent, fully completed week to generate a recap for.
    """
    available_weeks = get_available_weeks_for_recap(current_date)
    if not available_weeks:
        return 1  # Fallback to Week 1 if no weeks are fully complete yet
    
    # Return the latest week in the list of available weeks
    return available_weeks[-1]

def debug_week_selection(current_date):
    """
    Debug function to show the output of all date-related helper functions.
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
        'week_1_start_date': get_nfl_week_1_start(get_nfl_season_year(current_date)).strftime('%Y-%m-%d')
    }
