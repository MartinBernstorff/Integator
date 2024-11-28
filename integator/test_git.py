from integator.git import Log


def test_deser_from_log():
    log = Log(n_statuses=2).get()
