#ifndef CALIBRATION_SAVE_LOG_H
#define CALIBRATION_SAVE_LOG_H
#define CAL_LOG_FILE "calibration_log.sav"
void cal_log_keep(const char *text);
int cal_log_dump(void);
#endif
