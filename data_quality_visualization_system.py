"""
Data Quality Visualization System
Comprehensive institutional-grade visualization and reporting for data accuracy monitoring
Integrates cross-validation, quality monitoring, and enhanced flow calculations
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import logging
from dataclasses import asdict

# Import our enhanced accuracy modules
try:
    from enhanced_cross_validation_engine import enhanced_cross_validator, ValidationResult
    from real_time_quality_monitor import real_time_quality_monitor, QualityMetrics, QualityAlert
    from enhanced_options_flow_calculator import enhanced_options_flow_calculator, FlowAnalysisResult
except ImportError as e:
    logging.warning(f"Import warning in visualization system: {e}")

class DataQualityVisualizationSystem:
    """
    Institutional-grade data quality visualization and reporting system
    Combines all accuracy improvements into comprehensive dashboards
    """
    
    def __init__(self):
        self.visualization_config = {
            'quality_colors': {
                'excellent': '#00C851',    # Green
                'good': '#39CCCC',         # Teal  
                'fair': '#FF851B',         # Orange
                'poor': '#FF4444',         # Red
                'unknown': '#6C757D'       # Gray
            },
            'confidence_thresholds': {
                'high': 80,
                'medium': 60,
                'low': 40
            },
            'alert_severities': {
                'CRITICAL': {'color': '#FF4444', 'icon': '🚨'},
                'WARNING': {'color': '#FF851B', 'icon': '⚠️'},
                'INFO': {'color': '#17A2B8', 'icon': 'ℹ️'}
            }
        }
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def render_quality_dashboard(self, symbol: str, market_data: Dict, 
                               flow_data: Dict, fetch_start_time: float = None) -> Dict:
        """
        Render comprehensive data quality dashboard for a symbol
        Returns quality insights and renders Streamlit components
        """
        try:
            # 1. Cross-validation analysis
            validation_result = self._perform_cross_validation(symbol, market_data)
            
            # 2. Real-time quality monitoring
            quality_metrics = self._perform_quality_monitoring(symbol, market_data, fetch_start_time)
            
            # 3. Enhanced flow analysis
            flow_analysis = self._perform_flow_analysis(symbol, flow_data)
            
            # 4. Render quality overview section
            self._render_quality_overview(symbol, validation_result, quality_metrics, flow_analysis)
            
            # 5. Render detailed quality metrics
            self._render_detailed_metrics(validation_result, quality_metrics, flow_analysis)
            
            # 6. Render quality alerts and warnings
            self._render_quality_alerts(symbol, validation_result, quality_metrics)
            
            # 7. Render historical quality trends (if available)
            self._render_quality_trends(symbol)
            
            # Return comprehensive quality summary
            return self._create_quality_summary(validation_result, quality_metrics, flow_analysis)
            
        except Exception as e:
            self.logger.error(f"Quality dashboard rendering failed for {symbol}: {e}")
            st.error(f"❌ Quality Dashboard Error: {str(e)}")
            return {'error': str(e)}
    
    def _perform_cross_validation(self, symbol: str, market_data: Dict) -> ValidationResult:
        """Perform cross-validation analysis"""
        try:
            return enhanced_cross_validator.validate_market_data(symbol, market_data)
        except Exception as e:
            self.logger.warning(f"Cross-validation failed for {symbol}: {e}")
            # Return fallback result
            return ValidationResult(
                symbol=symbol,
                consensus_score=50,
                source_scores={},
                discrepancies=[f"Cross-validation error: {str(e)}"],
                confidence_level=30,
                validation_timestamp=datetime.now(),
                primary_source='unknown',
                backup_sources=[],
                price_consistency=False,
                volume_consistency=False,
                historical_consistency=False
            )
    
    def _perform_quality_monitoring(self, symbol: str, market_data: Dict, 
                                  fetch_start_time: float = None) -> QualityMetrics:
        """Perform real-time quality monitoring"""
        try:
            return real_time_quality_monitor.evaluate_data_quality(symbol, market_data, fetch_start_time)
        except Exception as e:
            self.logger.warning(f"Quality monitoring failed for {symbol}: {e}")
            # Return fallback metrics
            return QualityMetrics(
                symbol=symbol,
                overall_score=50,
                freshness_score=50,
                volume_score=50,
                price_score=50,
                historical_score=50,
                anomaly_flags=[f"Monitoring error: {str(e)}"],
                quality_trend='UNKNOWN',
                last_update=datetime.now(),
                data_latency_ms=0.0,
                confidence_level=30
            )
    
    def _perform_flow_analysis(self, symbol: str, flow_data: Dict) -> FlowAnalysisResult:
        """Perform enhanced flow analysis"""
        try:
            return enhanced_options_flow_calculator.calculate_enhanced_flow(symbol, flow_data)
        except Exception as e:
            self.logger.warning(f"Flow analysis failed for {symbol}: {e}")
            # Return fallback result
            return FlowAnalysisResult(
                symbol=symbol,
                total_call_volume=0,
                total_put_volume=0,
                weighted_call_dominance=50.0,
                weighted_put_dominance=50.0,
                flow_intensity_score=0,
                time_decay_adjusted_ratio=1.0,
                unusual_activity_flags=[f"Analysis error: {str(e)}"],
                confidence_score=30,
                dominant_expiration='unknown',
                flow_trend='NEUTRAL',
                institutional_bias='BALANCED',
                calculation_timestamp=datetime.now()
            )
    
    def _render_quality_overview(self, symbol: str, validation_result: ValidationResult,
                               quality_metrics: QualityMetrics, flow_analysis: FlowAnalysisResult):
        """Render quality overview section with badges and key metrics"""
        
        st.markdown("### 🎯 Data Quality Overview")
        
        # Create columns for quality badges
        badge_cols = st.columns(4)
        
        with badge_cols[0]:
            # Cross-validation badge
            consensus_color = self._get_quality_color(validation_result.consensus_score)
            st.markdown(f"""
            <div style="background-color: {consensus_color}; padding: 10px; border-radius: 8px; text-align: center; color: white;">
                <strong>Cross-Validation</strong><br>
                <span style="font-size: 24px;">{validation_result.consensus_score}%</span><br>
                <small>Consensus Score</small>
            </div>
            """, unsafe_allow_html=True)
        
        with badge_cols[1]:
            # Quality monitoring badge
            quality_color = self._get_quality_color(quality_metrics.overall_score)
            st.markdown(f"""
            <div style="background-color: {quality_color}; padding: 10px; border-radius: 8px; text-align: center; color: white;">
                <strong>Real-Time Quality</strong><br>
                <span style="font-size: 24px;">{quality_metrics.overall_score}%</span><br>
                <small>Overall Score</small>
            </div>
            """, unsafe_allow_html=True)
        
        with badge_cols[2]:
            # Flow analysis badge
            flow_color = self._get_quality_color(flow_analysis.confidence_score)
            st.markdown(f"""
            <div style="background-color: {flow_color}; padding: 10px; border-radius: 8px; text-align: center; color: white;">
                <strong>Flow Analysis</strong><br>
                <span style="font-size: 24px;">{flow_analysis.confidence_score}%</span><br>
                <small>Confidence</small>
            </div>
            """, unsafe_allow_html=True)
        
        with badge_cols[3]:
            # Combined confidence badge
            combined_confidence = self._calculate_combined_confidence(
                validation_result, quality_metrics, flow_analysis
            )
            combined_color = self._get_quality_color(combined_confidence)
            st.markdown(f"""
            <div style="background-color: {combined_color}; padding: 10px; border-radius: 8px; text-align: center; color: white;">
                <strong>Combined Score</strong><br>
                <span style="font-size: 24px;">{combined_confidence}%</span><br>
                <small>Overall Confidence</small>
            </div>
            """, unsafe_allow_html=True)
        
        # Quality insights row
        st.markdown("---")
        insight_cols = st.columns(3)
        
        with insight_cols[0]:
            st.metric(
                label="Data Latency", 
                value=f"{quality_metrics.data_latency_ms:.1f}ms",
                delta=None
            )
        
        with insight_cols[1]:
            st.metric(
                label="Flow Trend", 
                value=flow_analysis.flow_trend,
                delta=None
            )
        
        with insight_cols[2]:
            total_discrepancies = len(validation_result.discrepancies) + len(quality_metrics.anomaly_flags)
            st.metric(
                label="Quality Flags", 
                value=total_discrepancies,
                delta=None
            )
    
    def _render_detailed_metrics(self, validation_result: ValidationResult,
                               quality_metrics: QualityMetrics, flow_analysis: FlowAnalysisResult):
        """Render detailed quality metrics with charts"""
        
        st.markdown("### 📊 Detailed Quality Analysis")
        
        detail_tabs = st.tabs(["Cross-Validation", "Quality Monitoring", "Flow Analysis", "Performance"])
        
        with detail_tabs[0]:
            self._render_cross_validation_details(validation_result)
        
        with detail_tabs[1]:
            self._render_quality_monitoring_details(quality_metrics)
        
        with detail_tabs[2]:
            self._render_flow_analysis_details(flow_analysis)
        
        with detail_tabs[3]:
            self._render_performance_metrics()
    
    def _render_cross_validation_details(self, validation_result: ValidationResult):
        """Render cross-validation analysis details"""
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Source Scores")
            
            # Create source scores chart
            if validation_result.source_scores:
                source_df = pd.DataFrame([
                    {'Source': source, 'Score': score} 
                    for source, score in validation_result.source_scores.items()
                ])
                
                fig = px.bar(
                    source_df, 
                    x='Source', 
                    y='Score',
                    title='Data Source Quality Scores',
                    color='Score',
                    color_continuous_scale='RdYlGn',
                    range_color=[0, 100]
                )
                fig.update_layout(height=300)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No source scores available")
        
        with col2:
            st.markdown("#### Validation Status")
            
            # Validation status indicators
            status_indicators = [
                ("Price Consistency", validation_result.price_consistency),
                ("Volume Consistency", validation_result.volume_consistency), 
                ("Historical Consistency", validation_result.historical_consistency)
            ]
            
            for indicator, status in status_indicators:
                status_icon = "✅" if status else "❌"
                st.markdown(f"**{indicator}**: {status_icon}")
            
            st.markdown("#### Primary Source")
            st.info(f"**{validation_result.primary_source}**")
            
            if validation_result.backup_sources:
                st.markdown("#### Backup Sources")
                for source in validation_result.backup_sources:
                    st.markdown(f"• {source}")
        
        # Discrepancies section
        if validation_result.discrepancies:
            st.markdown("#### ⚠️ Discrepancies Found")
            for i, discrepancy in enumerate(validation_result.discrepancies, 1):
                st.warning(f"{i}. {discrepancy}")
    
    def _render_quality_monitoring_details(self, quality_metrics: QualityMetrics):
        """Render quality monitoring details"""
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Quality Breakdown")
            
            # Quality scores radar chart
            scores = [
                quality_metrics.freshness_score,
                quality_metrics.volume_score,
                quality_metrics.price_score,
                quality_metrics.historical_score
            ]
            categories = ['Freshness', 'Volume', 'Price', 'Historical']
            
            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(
                r=scores + [scores[0]],  # Close the polygon
                theta=categories + [categories[0]],
                fill='toself',
                name='Quality Scores',
                line_color='rgb(67, 156, 239)'
            ))
            
            fig.update_layout(
                polar=dict(
                    radialaxis=dict(
                        visible=True,
                        range=[0, 100]
                    )),
                showlegend=False,
                title="Quality Score Breakdown",
                height=300
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("#### Quality Metrics")
            
            # Individual metrics
            metrics = [
                ("Overall Score", quality_metrics.overall_score, "%"),
                ("Freshness Score", quality_metrics.freshness_score, "%"),
                ("Volume Score", quality_metrics.volume_score, "%"),
                ("Price Score", quality_metrics.price_score, "%"),
                ("Historical Score", quality_metrics.historical_score, "%"),
                ("Confidence Level", quality_metrics.confidence_level, "%"),
                ("Data Latency", quality_metrics.data_latency_ms, "ms")
            ]
            
            for metric_name, value, unit in metrics:
                if isinstance(value, float):
                    display_value = f"{value:.1f}{unit}"
                else:
                    display_value = f"{value}{unit}"
                st.metric(metric_name, display_value)
            
            st.markdown("#### Quality Trend")
            trend_icon = {"IMPROVING": "📈", "STABLE": "➡️", "DEGRADING": "📉"}.get(quality_metrics.quality_trend, "❓")
            st.markdown(f"**{quality_metrics.quality_trend}** {trend_icon}")
        
        # Anomaly flags
        if quality_metrics.anomaly_flags:
            st.markdown("#### 🔍 Anomaly Flags")
            for i, flag in enumerate(quality_metrics.anomaly_flags, 1):
                st.warning(f"{i}. {flag}")
    
    def _render_flow_analysis_details(self, flow_analysis: FlowAnalysisResult):
        """Render enhanced flow analysis details"""
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Volume Distribution")
            
            # Call/Put volume pie chart
            fig = go.Figure(data=[go.Pie(
                labels=['Calls', 'Puts'],
                values=[flow_analysis.total_call_volume, flow_analysis.total_put_volume],
                hole=0.4,
                marker_colors=['#00C851', '#FF4444']
            )])
            
            fig.update_layout(
                title="Call vs Put Volume",
                height=300,
                showlegend=True
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Flow metrics
            st.markdown("#### Flow Metrics")
            metrics = [
                ("Call Dominance", f"{flow_analysis.weighted_call_dominance:.1f}%"),
                ("Put Dominance", f"{flow_analysis.weighted_put_dominance:.1f}%"),
                ("Flow Intensity", f"{flow_analysis.flow_intensity_score}%"),
                ("Time-Adjusted Ratio", f"{flow_analysis.time_decay_adjusted_ratio:.2f}")
            ]
            
            for metric_name, value in metrics:
                st.metric(metric_name, value)
        
        with col2:
            st.markdown("#### Flow Analysis")
            
            # Key insights
            insights = [
                ("Flow Trend", flow_analysis.flow_trend),
                ("Institutional Bias", flow_analysis.institutional_bias),
                ("Dominant Expiration", flow_analysis.dominant_expiration),
                ("Confidence Score", f"{flow_analysis.confidence_score}%")
            ]
            
            for insight_name, value in insights:
                st.markdown(f"**{insight_name}**: {value}")
            
            # Volume breakdown
            st.markdown("#### Volume Breakdown")
            st.metric("Total Call Volume", f"{flow_analysis.total_call_volume:,}")
            st.metric("Total Put Volume", f"{flow_analysis.total_put_volume:,}")
            
            total_volume = flow_analysis.total_call_volume + flow_analysis.total_put_volume
            st.metric("Total Volume", f"{total_volume:,}")
        
        # Unusual activity flags
        if flow_analysis.unusual_activity_flags:
            st.markdown("#### 🚨 Unusual Activity")
            for i, flag in enumerate(flow_analysis.unusual_activity_flags, 1):
                st.error(f"{i}. {flag}")
    
    def _render_performance_metrics(self):
        """Render system performance metrics"""
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Cross-Validation Performance")
            try:
                cv_summary = enhanced_cross_validator.get_validation_summary()
                if 'total_validations' in cv_summary:
                    st.metric("Total Validations", cv_summary['total_validations'])
                    if cv_summary['total_validations'] > 0:
                        st.metric("Avg Consensus Score", f"{cv_summary['avg_consensus_score']:.1f}%")
                        st.metric("High Quality %", f"{cv_summary['high_quality_percentage']:.1f}%")
                else:
                    st.info("No validation data available")
            except Exception as e:
                st.error(f"Cross-validation metrics error: {e}")
        
        with col2:
            st.markdown("#### Quality Monitor Performance")
            try:
                quality_summary = real_time_quality_monitor.get_quality_summary()
                if 'total_symbols_monitored' in quality_summary:
                    st.metric("Symbols Monitored", quality_summary['total_symbols_monitored'])
                    if quality_summary['total_symbols_monitored'] > 0:
                        st.metric("Avg Quality Score", f"{quality_summary['average_quality_score']:.1f}%")
                        st.metric("Evaluation Time", f"{quality_summary['avg_evaluation_time_ms']:.1f}ms")
                else:
                    st.info("No monitoring data available")
            except Exception as e:
                st.error(f"Quality monitor metrics error: {e}")
        
        # Flow calculator performance
        st.markdown("#### Flow Calculator Performance")
        try:
            flow_summary = enhanced_options_flow_calculator.get_flow_summary()
            if 'total_symbols_analyzed' in flow_summary:
                flow_cols = st.columns(4)
                with flow_cols[0]:
                    st.metric("Symbols Analyzed", flow_summary['total_symbols_analyzed'])
                with flow_cols[1]:
                    st.metric("Avg Confidence", f"{flow_summary['average_confidence_score']:.1f}%")
                with flow_cols[2]:
                    st.metric("Avg Intensity", f"{flow_summary['average_flow_intensity']:.1f}%")
                with flow_cols[3]:
                    st.metric("Calculation Time", f"{flow_summary['avg_calculation_time_ms']:.1f}ms")
            else:
                st.info("No flow analysis data available")
        except Exception as e:
            st.error(f"Flow calculator metrics error: {e}")
    
    def _render_quality_alerts(self, symbol: str, validation_result: ValidationResult,
                             quality_metrics: QualityMetrics):
        """Render quality alerts and warnings"""
        
        # Get recent alerts
        try:
            recent_alerts = real_time_quality_monitor.get_recent_alerts(limit=5)
            
            if recent_alerts:
                st.markdown("### 🚨 Recent Quality Alerts")
                
                for alert in recent_alerts:
                    severity_config = self.visualization_config['alert_severities'].get(
                        alert.severity, {'color': '#6C757D', 'icon': '⚠️'}
                    )
                    
                    with st.expander(f"{severity_config['icon']} {alert.severity}: {alert.message}"):
                        st.markdown(f"**Symbol**: {alert.symbol}")
                        st.markdown(f"**Metric Affected**: {alert.metric_affected}")
                        st.markdown(f"**Current Score**: {alert.current_score}%")
                        st.markdown(f"**Threshold**: {alert.threshold}%")
                        st.markdown(f"**Time**: {alert.timestamp.strftime('%H:%M:%S')}")
                        st.markdown(f"**Recommended Action**: {alert.recommended_action}")
                        
                        # Show alert in appropriate color
                        st.markdown(
                            f'<div style="padding: 10px; background-color: {severity_config["color"]}20; '
                            f'border-left: 4px solid {severity_config["color"]}; border-radius: 4px;">'
                            f'<strong>{alert.severity}</strong>: {alert.message}</div>',
                            unsafe_allow_html=True
                        )
        except Exception as e:
            st.info("No recent alerts available")
    
    def _render_quality_trends(self, symbol: str):
        """Render historical quality trends if available"""
        try:
            # Get quality history for the symbol
            if hasattr(real_time_quality_monitor, 'quality_history') and symbol in real_time_quality_monitor.quality_history:
                history = real_time_quality_monitor.quality_history[symbol]
                
                if len(history) > 1:
                    st.markdown("### 📈 Quality Trends")
                    
                    # Create trend chart
                    timestamps = [q.last_update for q in history[-20:]]  # Last 20 measurements
                    overall_scores = [q.overall_score for q in history[-20:]]
                    confidence_levels = [q.confidence_level for q in history[-20:]]
                    
                    fig = go.Figure()
                    
                    fig.add_trace(go.Scatter(
                        x=timestamps,
                        y=overall_scores,
                        mode='lines+markers',
                        name='Overall Quality',
                        line=dict(color='#007bff', width=2)
                    ))
                    
                    fig.add_trace(go.Scatter(
                        x=timestamps,
                        y=confidence_levels,
                        mode='lines+markers',
                        name='Confidence Level',
                        line=dict(color='#28a745', width=2)
                    ))
                    
                    fig.update_layout(
                        title=f'Quality Trends - {symbol}',
                        xaxis_title='Time',
                        yaxis_title='Score (%)',
                        yaxis=dict(range=[0, 100]),
                        height=300
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            pass  # Silently skip if trends not available
    
    def _get_quality_color(self, score: int) -> str:
        """Get color based on quality score"""
        if score >= 85:
            return self.visualization_config['quality_colors']['excellent']
        elif score >= 70:
            return self.visualization_config['quality_colors']['good']
        elif score >= 50:
            return self.visualization_config['quality_colors']['fair']
        elif score > 0:
            return self.visualization_config['quality_colors']['poor']
        else:
            return self.visualization_config['quality_colors']['unknown']
    
    def _calculate_combined_confidence(self, validation_result: ValidationResult,
                                     quality_metrics: QualityMetrics, 
                                     flow_analysis: FlowAnalysisResult) -> int:
        """Calculate combined confidence score"""
        try:
            # Weighted average of all confidence scores
            weights = {
                'validation': 0.35,
                'quality': 0.35,
                'flow': 0.30
            }
            
            combined = (
                validation_result.confidence_level * weights['validation'] +
                quality_metrics.confidence_level * weights['quality'] +
                flow_analysis.confidence_score * weights['flow']
            )
            
            return int(min(100, max(0, combined)))
        except Exception:
            return 50  # Default moderate confidence
    
    def _create_quality_summary(self, validation_result: ValidationResult,
                              quality_metrics: QualityMetrics, 
                              flow_analysis: FlowAnalysisResult) -> Dict:
        """Create comprehensive quality summary"""
        try:
            combined_confidence = self._calculate_combined_confidence(
                validation_result, quality_metrics, flow_analysis
            )
            
            return {
                'combined_confidence': combined_confidence,
                'validation_score': validation_result.consensus_score,
                'quality_score': quality_metrics.overall_score,
                'flow_confidence': flow_analysis.confidence_score,
                'total_discrepancies': len(validation_result.discrepancies) + len(quality_metrics.anomaly_flags),
                'data_latency_ms': quality_metrics.data_latency_ms,
                'flow_trend': flow_analysis.flow_trend,
                'quality_trend': quality_metrics.quality_trend,
                'institutional_bias': flow_analysis.institutional_bias,
                'primary_source': validation_result.primary_source,
                'evaluation_timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"Error creating quality summary: {e}")
            return {'error': str(e)}
    
    def render_global_quality_dashboard(self) -> Dict:
        """Render global quality dashboard for all monitored symbols"""
        try:
            st.markdown("### 🌐 Global Data Quality Dashboard")
            
            # Get global summaries
            cv_summary = enhanced_cross_validator.get_validation_summary()
            quality_summary = real_time_quality_monitor.get_quality_summary()
            flow_summary = enhanced_options_flow_calculator.get_flow_summary()
            
            # Global metrics overview
            global_cols = st.columns(4)
            
            with global_cols[0]:
                st.metric(
                    "Total Validations", 
                    cv_summary.get('total_validations', 0)
                )
            
            with global_cols[1]:
                st.metric(
                    "Avg Quality Score", 
                    f"{quality_summary.get('average_quality_score', 0):.1f}%"
                )
            
            with global_cols[2]:
                st.metric(
                    "Symbols Monitored", 
                    quality_summary.get('total_symbols_monitored', 0)
                )
            
            with global_cols[3]:
                st.metric(
                    "Recent Alerts", 
                    quality_summary.get('alerts_last_hour', 0)
                )
            
            # Performance metrics chart
            if cv_summary.get('total_validations', 0) > 0:
                st.markdown("#### System Performance")
                
                perf_data = {
                    'Cross-Validation': cv_summary.get('avg_consensus_score', 0),
                    'Quality Monitoring': quality_summary.get('average_quality_score', 0),
                    'Flow Analysis': flow_summary.get('average_confidence_score', 0)
                }
                
                fig = px.bar(
                    x=list(perf_data.keys()),
                    y=list(perf_data.values()),
                    title='System Performance Overview',
                    labels={'x': 'Component', 'y': 'Score (%)'},
                    color=list(perf_data.values()),
                    color_continuous_scale='RdYlGn',
                    range_color=[0, 100]
                )
                fig.update_layout(height=300)
                st.plotly_chart(fig, use_container_width=True)
            
            return {
                'cross_validation': cv_summary,
                'quality_monitoring': quality_summary,
                'flow_analysis': flow_summary
            }
            
        except Exception as e:
            self.logger.error(f"Global dashboard rendering failed: {e}")
            st.error(f"❌ Global Dashboard Error: {str(e)}")
            return {'error': str(e)}

# Global instance for easy access
data_quality_visualizer = DataQualityVisualizationSystem()