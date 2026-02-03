#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
W&B Sweeps 结果分析工具
分析超参数搜索结果，提取最优参数配置
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import wandb
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from typing import Dict, List, Optional
import json

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'STHeiti', 'PingFang SC']
plt.rcParams['axes.unicode_minus'] = False


class SweepAnalyzer:
    """Sweep 结果分析器"""
    
    def __init__(self, entity: str = None, project: str = None):
        """
        初始化分析器
        
        Args:
            entity: W&B 用户名或团队名
            project: W&B 项目名称
        """
        self.entity = entity
        self.project = project
        self.api = wandb.Api()
    
    def get_sweep_runs(self, sweep_id: str) -> pd.DataFrame:
        """
        获取 sweep 的所有运行结果
        
        Args:
            sweep_id: Sweep ID
            
        Returns:
            包含所有运行结果的 DataFrame
        """
        sweep_path = f"{self.entity}/{self.project}/{sweep_id}" if self.entity else sweep_id
        sweep = self.api.sweep(sweep_path)
        
        runs_data = []
        for run in sweep.runs:
            run_data = {
                'run_id': run.id,
                'run_name': run.name,
                'state': run.state
            }
            # 添加配置参数
            run_data.update(run.config)
            # 添加汇总指标
            run_data.update(run.summary._json_dict)
            runs_data.append(run_data)
        
        return pd.DataFrame(runs_data)
    
    def get_best_runs(self, sweep_id: str, metric: str = 'avg_return_rate', 
                      top_n: int = 5, ascending: bool = False) -> pd.DataFrame:
        """
        获取最佳运行结果
        
        Args:
            sweep_id: Sweep ID
            metric: 排序指标
            top_n: 返回前 N 个结果
            ascending: 是否升序排列
            
        Returns:
            最佳运行结果 DataFrame
        """
        df = self.get_sweep_runs(sweep_id)
        
        # 过滤掉失败的运行
        df = df[df['state'] == 'finished']
        
        if metric not in df.columns:
            print(f"Warning: metric '{metric}' not found in results")
            return df.head(top_n)
        
        # 排序并返回
        return df.sort_values(metric, ascending=ascending).head(top_n)
    
    def analyze_parameter_importance(self, sweep_id: str, 
                                     target_metric: str = 'avg_return_rate') -> Dict:
        """
        分析参数重要性
        
        Args:
            sweep_id: Sweep ID
            target_metric: 目标指标
            
        Returns:
            参数重要性分析结果
        """
        df = self.get_sweep_runs(sweep_id)
        df = df[df['state'] == 'finished']
        
        if target_metric not in df.columns:
            print(f"Target metric '{target_metric}' not found")
            return {}
        
        # 识别参数列（排除元数据和指标）
        exclude_cols = ['run_id', 'run_name', 'state', '_timestamp', '_runtime', 
                       '_step', '_wandb', target_metric]
        param_cols = [col for col in df.columns if col not in exclude_cols 
                     and not col.startswith('_') and df[col].dtype in ['float64', 'int64']]
        
        importance = {}
        
        for param in param_cols:
            if df[param].nunique() > 1:
                # 计算与目标指标的相关性
                correlation = df[param].corr(df[target_metric])
                if not np.isnan(correlation):
                    importance[param] = abs(correlation)
        
        # 按重要性排序
        importance = dict(sorted(importance.items(), key=lambda x: x[1], reverse=True))
        
        return importance
    
    def plot_parameter_importance(self, sweep_id: str, 
                                  target_metric: str = 'avg_return_rate',
                                  save_path: str = None):
        """
        绘制参数重要性图
        """
        importance = self.analyze_parameter_importance(sweep_id, target_metric)
        
        if not importance:
            print("No importance data to plot")
            return
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        params = list(importance.keys())[:15]  # 只显示前15个
        values = [importance[p] for p in params]
        
        colors = plt.cm.RdYlGn(np.linspace(0.2, 0.8, len(params)))[::-1]
        
        bars = ax.barh(params, values, color=colors)
        ax.set_xlabel('相关性 (绝对值)')
        ax.set_title(f'参数重要性分析 - 目标: {target_metric}')
        ax.set_xlim(0, 1)
        
        # 添加数值标签
        for bar, val in zip(bars, values):
            ax.text(bar.get_width() + 0.02, bar.get_y() + bar.get_height()/2, 
                   f'{val:.3f}', va='center')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"图表已保存: {save_path}")
        
        plt.show()
    
    def plot_parallel_coordinates(self, sweep_id: str,
                                  target_metric: str = 'avg_return_rate',
                                  params: List[str] = None,
                                  save_path: str = None):
        """
        绘制平行坐标图（可视化参数组合）
        """
        df = self.get_sweep_runs(sweep_id)
        df = df[df['state'] == 'finished']
        
        if target_metric not in df.columns:
            print(f"Target metric '{target_metric}' not found")
            return
        
        # 选择参数
        if params is None:
            importance = self.analyze_parameter_importance(sweep_id, target_metric)
            params = list(importance.keys())[:6]  # 选择最重要的6个参数
        
        # 添加目标指标
        plot_cols = params + [target_metric]
        plot_df = df[plot_cols].dropna()
        
        # 归一化
        normalized = (plot_df - plot_df.min()) / (plot_df.max() - plot_df.min())
        
        fig, ax = plt.subplots(figsize=(14, 6))
        
        # 按目标指标着色
        colors = plt.cm.RdYlGn(normalized[target_metric])
        
        for i, row in normalized.iterrows():
            ax.plot(range(len(plot_cols)), row.values, 
                   color=colors[i], alpha=0.5, linewidth=1)
        
        ax.set_xticks(range(len(plot_cols)))
        ax.set_xticklabels(plot_cols, rotation=45, ha='right')
        ax.set_ylabel('归一化值')
        ax.set_title(f'平行坐标图 - 参数组合可视化\n(绿色 = 高 {target_metric})')
        
        # 添加颜色条
        sm = plt.cm.ScalarMappable(cmap='RdYlGn', 
                                   norm=plt.Normalize(vmin=df[target_metric].min(),
                                                     vmax=df[target_metric].max()))
        sm.set_array([])
        cbar = plt.colorbar(sm, ax=ax)
        cbar.set_label(target_metric)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"图表已保存: {save_path}")
        
        plt.show()
    
    def export_best_config(self, sweep_id: str, 
                          metric: str = 'avg_return_rate',
                          output_path: str = None) -> Dict:
        """
        导出最佳配置
        
        Args:
            sweep_id: Sweep ID
            metric: 排序指标
            output_path: 输出文件路径
            
        Returns:
            最佳配置字典
        """
        best_runs = self.get_best_runs(sweep_id, metric, top_n=1)
        
        if best_runs.empty:
            print("No successful runs found")
            return {}
        
        best_run = best_runs.iloc[0]
        
        # 提取配置参数（排除元数据）
        exclude_keys = ['run_id', 'run_name', 'state', '_timestamp', '_runtime', 
                       '_step', '_wandb']
        
        config = {}
        for key, value in best_run.items():
            if key not in exclude_keys and not key.startswith('_'):
                # 处理 NaN 值
                if pd.isna(value):
                    continue
                config[key] = value
        
        result = {
            'sweep_id': sweep_id,
            'best_run_id': best_run['run_id'],
            'metric': metric,
            'metric_value': best_run.get(metric, None),
            'config': config
        }
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False, default=str)
            print(f"最佳配置已保存: {output_path}")
        
        return result
    
    def generate_report(self, sweep_id: str, 
                       target_metric: str = 'avg_return_rate',
                       output_dir: str = 'sweep_analysis'):
        """
        生成完整分析报告
        """
        os.makedirs(output_dir, exist_ok=True)
        
        print("=" * 60)
        print(f"Sweep 分析报告: {sweep_id}")
        print("=" * 60)
        
        # 获取所有运行
        df = self.get_sweep_runs(sweep_id)
        finished = df[df['state'] == 'finished']
        
        print(f"\n【运行统计】")
        print(f"  总运行数: {len(df)}")
        print(f"  成功完成: {len(finished)}")
        print(f"  失败/中断: {len(df) - len(finished)}")
        
        if target_metric in finished.columns:
            print(f"\n【{target_metric} 统计】")
            print(f"  最大值: {finished[target_metric].max():.6f}")
            print(f"  最小值: {finished[target_metric].min():.6f}")
            print(f"  平均值: {finished[target_metric].mean():.6f}")
            print(f"  标准差: {finished[target_metric].std():.6f}")
        
        # 最佳运行
        print(f"\n【最佳配置 Top 5】")
        best_runs = self.get_best_runs(sweep_id, target_metric, top_n=5)
        for i, row in best_runs.iterrows():
            print(f"\n  #{best_runs.index.get_loc(i)+1} (Run: {row['run_name']})")
            if target_metric in row:
                print(f"    {target_metric}: {row[target_metric]:.6f}")
        
        # 参数重要性
        print(f"\n【参数重要性】")
        importance = self.analyze_parameter_importance(sweep_id, target_metric)
        for param, imp in list(importance.items())[:10]:
            print(f"  {param}: {imp:.4f}")
        
        # 导出最佳配置
        best_config = self.export_best_config(
            sweep_id, 
            target_metric,
            f"{output_dir}/best_config_{sweep_id}.json"
        )
        
        # 生成可视化
        self.plot_parameter_importance(
            sweep_id, target_metric,
            f"{output_dir}/param_importance_{sweep_id}.png"
        )
        
        self.plot_parallel_coordinates(
            sweep_id, target_metric,
            save_path=f"{output_dir}/parallel_coords_{sweep_id}.png"
        )
        
        print(f"\n分析报告已保存到: {output_dir}/")
        print("=" * 60)
        
        return {
            'sweep_id': sweep_id,
            'total_runs': len(df),
            'successful_runs': len(finished),
            'best_config': best_config,
            'parameter_importance': importance
        }


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='W&B Sweep 结果分析')
    parser.add_argument('--sweep-id', '-s', required=True, help='Sweep ID')
    parser.add_argument('--entity', '-e', default=None, help='W&B 用户名/团队名')
    parser.add_argument('--project', '-p', default=None, help='W&B 项目名')
    parser.add_argument('--metric', '-m', default='avg_return_rate', 
                       help='目标指标 (默认: avg_return_rate)')
    parser.add_argument('--output', '-o', default='sweep_analysis',
                       help='输出目录 (默认: sweep_analysis)')
    
    args = parser.parse_args()
    
    analyzer = SweepAnalyzer(entity=args.entity, project=args.project)
    analyzer.generate_report(
        sweep_id=args.sweep_id,
        target_metric=args.metric,
        output_dir=args.output
    )


if __name__ == "__main__":
    main()
