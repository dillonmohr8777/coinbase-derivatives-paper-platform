"""Radar tests — the sample prompt must yield a ranked, cited report from fixtures."""

from app.radar import FixtureDarkPool, FixtureOptionsFlow, FixtureSecFilings, Radar

SAMPLE = "Find me whale trades where institutions are positioning before the move."


def test_radar_ranks_and_cites():
    radar = Radar(
        connectors=[FixtureOptionsFlow(), FixtureDarkPool(), FixtureSecFilings()],
        min_signals=2,
    )
    report = radar.find_whale_trades(SAMPLE, symbols=["AAPL", "MSFT", "NVDA"])

    assert report.query == SAMPLE
    assert report.rows, "expected at least one ranked ticker"
    # Ranked descending by score.
    scores = [r.score for r in report.rows]
    assert scores == sorted(scores, reverse=True)
    # Every ranked row carries its evidence trail (citations) from >= 2 sources.
    for row in report.rows:
        assert len({s.source for s in row.signals}) >= 2


def test_min_signals_threshold_filters():
    # With min_signals=99 nothing can qualify.
    radar = Radar([FixtureOptionsFlow()], min_signals=99)
    report = radar.find_whale_trades(SAMPLE, symbols=["AAPL"])
    assert report.rows == []
