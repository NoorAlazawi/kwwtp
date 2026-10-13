from analytics.models import Alarm


def generate_alarms(reading):
    reading.alarms.filter(is_predicted=False).delete()
    crit = warn = 0
    for i, d in enumerate(reading.diagnoses.all(), start=1):
        if d.status in ("warning", "underloaded"):
            level = Alarm.Level.WARNING; warn += 1
        elif d.status == "critical":
            level = Alarm.Level.CRITICAL; crit += 1
        else:
            continue
        Alarm.objects.create(
            reading=reading, parameter=d.parameter,
            alarm_code=f"AL{i:03d}", level=level,
            value=d.value, message=d.cause, action=d.action,
            is_predicted=False,
        )
    return crit, warn
