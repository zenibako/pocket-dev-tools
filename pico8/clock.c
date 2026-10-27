// Lua seeds its string hash with time(). Use the same virtual frame clock as
// the fullframe bridge's gettimeofday/clock_gettime, never wall-clock time.
#include "frame.h"
#include <time.h>

time_t time(time_t *out) {
    time_t now = (time_t)(frame_clock / 1000000000ull);
    if (out) *out = now;
    return now;
}
