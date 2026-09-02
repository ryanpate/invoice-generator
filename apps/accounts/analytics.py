"""
One-shot GA4 conversion events queued server-side.

Two of the conversions worth measuring do not happen on a page the browser
is already sitting on: signup finishes with a redirect, and a subscription
finishes with a redirect back from Stripe. Firing them from a fixed page
does not work either -- /pricing/ sends a buyer to signup with
?next=<checkout>, so a paying user never loads the dashboard.

So the server drops the event in the session and the next rendered page
emits it, once. Params are rendered with json_script, which is XSS-safe.
"""

SESSION_KEY = 'ga_events'


def queue_event(request, name, **params):
    """Queue a GA4 event to fire on the next page this session renders."""
    session = getattr(request, 'session', None)
    if session is None:
        return
    events = session.get(SESSION_KEY, [])
    events.append({'name': name, 'params': params})
    session[SESSION_KEY] = events
    session.modified = True


def analytics_events(request):
    """Context processor: hand the queued events to the template and clear them.

    Only consumes the queue on GET. The signup POST renders a template of its
    own before redirecting (the welcome email body), which runs this processor
    and would swallow the event before any page the visitor actually sees. A
    conversion always lands on a subsequent GET, so gating on the method keeps
    the queue intact across the redirect. A POST that re-renders a form with
    errors likewise leaves the queue alone for the next real page view.
    """
    session = getattr(request, 'session', None)
    if session is None or getattr(request, 'method', None) != 'GET':
        return {'ga_events': []}
    events = session.pop(SESSION_KEY, None)
    if events:
        session.modified = True
    return {'ga_events': events or []}
