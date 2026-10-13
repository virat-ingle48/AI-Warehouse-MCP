from storage.lock import acquire_singleton_lock, release_singleton_lock


def test_first_instance_acquires_lock(tmp_path):
    lock_file = tmp_path / "test.lock"
    assert acquire_singleton_lock(lock_file) is True
    assert lock_file.exists()
    release_singleton_lock()


def test_second_instance_blocked_while_first_alive(tmp_path):
    lock_file = tmp_path / "test.lock"
    acquire_singleton_lock(lock_file)
    assert acquire_singleton_lock(lock_file) is False

    release_singleton_lock()


def test_concurrent_acquire_only_one_succeeds(tmp_path):
    lock_file = tmp_path / "test.lock"

    result_a = acquire_singleton_lock(lock_file)
    result_b = acquire_singleton_lock(lock_file)

    assert result_a is True
    assert result_b is False

    release_singleton_lock()


def test_stale_lock_is_reclaimed(tmp_path):
    lock_file = tmp_path / "test.lock"
    lock_file.write_text("999999999")

    assert acquire_singleton_lock(lock_file) is True
    release_singleton_lock()