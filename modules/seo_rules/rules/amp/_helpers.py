"""Heurística para detectar URLs AMP."""

AMP_URL_SQL = """
    (url LIKE '%/amp/%'
     OR url LIKE '%/amp'
     OR url LIKE '%?amp=1%'
     OR url LIKE '%?amp%'
     OR url LIKE '%&amp=1%'
     OR url LIKE '%.amp.html'
     OR url LIKE '%amp.html')
"""
