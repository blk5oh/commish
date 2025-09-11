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
    NFL seasons run from September of one year through January of the next year.
    The season is named after the year it starts in.
    """
    if current_date.month >= 9:  # September or later = current year's season
        return current_date.year
    else:  # January through August = previous year's season
        return current_date.year - 1

def get_nfl_week_1_start(season_year):
    """
    Calculates the start of NFL Week 1 for a given season.
    NFL typically starts the first Thursday after Labor Day (first Monday in September).
    But we'll use a simpler approximation: first Thursday of September.
    """
    # Find the first Thursday of September
    first_of_sept = datetime(season_year, 9, 1)
    
    # Find first Thursday (weekday 3)
    days_until_thursday = (3 - first_of_sept.weekday()) % 7
    if days_until_thursday == 0 and first_of_sept.weekday() != 3:
        days_until_thursday = 7
    
    first_thursday = first_of_sept + timedelta(days=days_until_thursday)
    
    # NFL actually starts the Thursday night game, but for simplicity,
    # let's use the preceding Wednesday as the "start" of Week 1
    # This accounts for when scoring typically begins
    week_1_start = first_thursday - timedelta(days=1)
    
    return week_1_start

def generate_nfl_schedule(season_year):
    """
    Generates the complete NFL schedule for a given season.
    Returns a dictionary mapping week start dates to week numbers.
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
    Dynamically determines the current NFL week based on the date.
    Automatically handles year transitions and doesn't require manual updates.
    """
    # Determine which NFL season we're in
    season_year = get_nfl_season_year(current_date)
    
    # Generate the schedule for this season
    schedule = generate_nfl_schedule(season_year)
    
    # Find the current week
    sorted_dates = sorted(schedule.keys(), reverse=True)
    
    for week_start_date in sorted_dates:
        if current_date >= week_start_date:
            return schedule[week_start_date]
    
    # If we're before the season starts, return Week 1
    return 1

def get_most_recent_completed_week(current_date):
    """
    Gets the most recent week that should have completed scoring.
    Accounts for the fact that Monday Night Football scores aren't 
    finalized until Tuesday morning.
    """
    current_week = get_current_week(current_date)
    
    # If it's Monday or early Tuesday, the previous week might not be finalized
    est = pytz.timezone('US/Eastern')
    current_est = current_date.astimezone(est) if current_date.tzinfo else est.localize(current_date)
    
    # If it's Monday or Tuesday before 6 AM EST, use the week before current
    if (current_est.weekday() == 0 or  # Monday
        (current_est.weekday() == 1 and current_est.hour < 6)):  # Tuesday before 6 AM
        return max(1, current_week - 1)
    
    # Otherwise, if we're in the middle of a week, the previous week should be complete
    # But if it's late in the week (Thu-Sun), current week games might be in progress
    if current_est.weekday() >= 3:  # Thursday or later
        return current_week  # Current week games are happening/just finished
    else:
        return max(1, current_week - 1)  # Use previous completed week

# Convenience function that matches your existing usage
def get_completed_week_for_recap():
    """
    Gets the week number that should be used for generating recaps.
    This is the most recent week with finalized scoring.
    """
    return get_most_recent_completed_week(datetime.now())
