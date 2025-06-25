from time import sleep, time as _test_perf_time
#from time import sleep, time, time as _test_perf_time
#from time import sleep

test_time = _test_perf_time()
print("test_time:", test_time)
print("Sleeping for one second.")
sleep(1)
#_test_perf_time.sleep(1)
print("Sleep complete.")
