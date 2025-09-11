# Replace the matchup display section in your generate_sleeper_summary function with:

# Get matchup data
blowout_match, blowout_diff = sleeper_helper.biggest_blowout_match_of_week(scoreboards)
close_match, close_diff = sleeper_helper.closest_match_of_week(scoreboards)

# Format blowout match display
if blowout_match and len(blowout_match) >= 2:
    blowout_winner = blowout_match[0]
    blowout_loser = blowout_match[1]
    blowout_text = f"{blowout_winner[0]} ({blowout_winner[1]:.1f}) vs {blowout_loser[0]} ({blowout_loser[1]:.1f})"
else:
    blowout_text = "No matchup data available"

# Format closest match display  
if close_match and len(close_match) >= 2:
    close_winner = close_match[0]
    close_loser = close_match[1]
    close_text = f"{close_winner[0]} ({close_winner[1]:.1f}) vs {close_loser[0]} ({close_loser[1]:.1f})"
else:
    close_text = "No matchup data available"

# Then in your summary_parts, replace the matchup section with:
f"### Matchup Highlights\n",
f"**Biggest Blowout:** {blowout_text} (Point Differential: **{blowout_diff:.2f}**)\n",
f"**Closest Game:** {close_text} (Point Differential: **{close_diff:.2f}**)\n",
