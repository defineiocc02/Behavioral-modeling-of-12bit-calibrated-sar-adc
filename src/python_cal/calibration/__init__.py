"""
calibration/ — SAR ADC 校准模块

主要接口:
  - ShenCalibrationController: 标准 Shen 2018 force-0/force-1 校准 (当前交付)

已废弃:
  - AsyncCalibrationController: 旧版 calDAC 搜索方案 (calibration_controller.py)
  - CalibrationReport: 旧版报告格式

历史 observable-alpha 实验已从生产模块依赖中移除；仅保留在未交付的
实验脚本中，不能作为验收入口。
"""
