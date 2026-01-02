import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
  RefreshControl,
  Dimensions,
  TouchableOpacity,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { LineChart, BarChart, PieChart } from 'react-native-chart-kit';
import { useTheme } from '../../contexts/ThemeContext';
import Header from '../../components/Header';
import apiService from '../../services/api';

const screenWidth = Dimensions.get('window').width;

export default function AnalyticsScreen() {
  const { theme, isDark } = useTheme();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [timePeriod, setTimePeriod] = useState<'month' | 'week'>('month');
  const [earningsData, setEarningsData] = useState<any>(null);
  const [categoryData, setCategoryData] = useState<any>(null);
  const [analytics, setAnalytics] = useState<any>(null);

  useEffect(() => {
    loadAnalytics();
  }, [timePeriod]);

  const loadAnalytics = async () => {
    try {
      setLoading(true);
      const [analyticsData, earningsBreakdown, categoryBreakdown] = await Promise.all([
        apiService.getWorkerAnalytics().catch(() => null),
        apiService.getEarningsBreakdown(timePeriod, 6).catch(() => []),
        apiService.getEarningsByCategory().catch(() => []),
      ]);

      setAnalytics(analyticsData);
      setEarningsData(earningsBreakdown);
      setCategoryData(categoryBreakdown);
    } catch (error) {
      console.error('Error loading analytics:', error);
    } finally {
      setLoading(false);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await loadAnalytics();
    setRefreshing(false);
  };

  const prepareEarningsChartData = () => {
    if (!earningsData || earningsData.length === 0) {
      return {
        labels: ['N/A'],
        datasets: [{ data: [0] }],
      };
    }

    const labels = earningsData.map((item: any) => item.period.substring(0, 3));
    const data = earningsData.map((item: any) => parseFloat(item.earnings) || 0);

    return {
      labels,
      datasets: [{ data, strokeWidth: 2 }],
    };
  };

  const prepareCategoryChartData = () => {
    if (!categoryData || categoryData.length === 0) {
      return [];
    }

    const colors = ['#0F766E', '#3B82F6', '#8B5CF6', '#F59E0B', '#EF4444', '#10B981'];
    
    return categoryData.slice(0, 6).map((item: any, index: number) => ({
      name: item.category,
      earnings: parseFloat(item.earnings) || 0,
      color: colors[index % colors.length],
      legendFontColor: theme.textSecondary,
      legendFontSize: 12,
    }));
  };

  const chartConfig = {
    backgroundColor: theme.surface,
    backgroundGradientFrom: theme.surface,
    backgroundGradientTo: theme.surface,
    decimalPlaces: 0,
    color: (opacity = 1) => `rgba(15, 118, 110, ${opacity})`,
    labelColor: (opacity = 1) => (isDark ? `rgba(255, 255, 255, ${opacity})` : `rgba(0, 0, 0, ${opacity})`),
    style: {
      borderRadius: 16,
    },
    propsForDots: {
      r: '6',
      strokeWidth: '2',
      stroke: theme.primary,
    },
  };

  const calculateSuccessRate = () => {
    if (!analytics) return 0;
    const total = analytics.total_applications || 0;
    const accepted = analytics.accepted_applications || 0;
    return total > 0 ? Math.round((accepted / total) * 100) : 0;
  };

  if (loading) {
    return (
      <View style={[styles.container, { backgroundColor: theme.background }]}>
        <StatusBar style={theme.statusBar} />
        <Header showBack />
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={theme.primary} />
          <Text style={[styles.loadingText, { color: theme.textSecondary }]}>
            Loading analytics...
          </Text>
        </View>
      </View>
    );
  }

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      <StatusBar style={theme.statusBar} />
      <Header showBack />

      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            tintColor={theme.primary}
            colors={[theme.primary]}
          />
        }
      >
        {/* Header */}
        <View style={styles.header}>
          <View style={styles.titleContainer}>
            <Ionicons name="analytics" size={28} color={theme.primary} />
            <Text style={[styles.title, { color: theme.text }]}>Analytics</Text>
          </View>
        </View>

        {/* Key Metrics */}
        <View style={styles.metricsGrid}>
          <View style={[styles.metricCard, { backgroundColor: theme.surface }]}>
            <Ionicons name="checkmark-circle" size={32} color="#10B981" />
            <Text style={[styles.metricValue, { color: theme.text }]}>
              {calculateSuccessRate()}%
            </Text>
            <Text style={[styles.metricLabel, { color: theme.textSecondary }]}>
              Success Rate
            </Text>
          </View>

          <View style={[styles.metricCard, { backgroundColor: theme.surface }]}>
            <Ionicons name="document-text" size={32} color={theme.primary} />
            <Text style={[styles.metricValue, { color: theme.text }]}>
              {analytics?.total_applications || 0}
            </Text>
            <Text style={[styles.metricLabel, { color: theme.textSecondary }]}>
              Applications
            </Text>
          </View>

          <View style={[styles.metricCard, { backgroundColor: theme.surface }]}>
            <Ionicons name="briefcase" size={32} color="#3B82F6" />
            <Text style={[styles.metricValue, { color: theme.text }]}>
              {analytics?.completed_jobs || 0}
            </Text>
            <Text style={[styles.metricLabel, { color: theme.textSecondary }]}>
              Completed
            </Text>
          </View>

          <View style={[styles.metricCard, { backgroundColor: theme.surface }]}>
            <Ionicons name="star" size={32} color="#F59E0B" />
            <Text style={[styles.metricValue, { color: theme.text }]}>
              {analytics?.average_rating || '0.0'}
            </Text>
            <Text style={[styles.metricLabel, { color: theme.textSecondary }]}>
              Avg Rating
            </Text>
          </View>
        </View>

        {/* Earnings Trend */}
        <View style={[styles.chartCard, { backgroundColor: theme.surface }]}>
          <View style={styles.chartHeader}>
            <Text style={[styles.chartTitle, { color: theme.text }]}>Earnings Trend</Text>
            <View style={styles.periodToggle}>
              <TouchableOpacity
                style={[
                  styles.periodButton,
                  timePeriod === 'week' && { backgroundColor: theme.primary },
                ]}
                onPress={() => setTimePeriod('week')}
              >
                <Text
                  style={[
                    styles.periodButtonText,
                    { color: timePeriod === 'week' ? '#FFFFFF' : theme.textSecondary },
                  ]}
                >
                  Week
                </Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[
                  styles.periodButton,
                  timePeriod === 'month' && { backgroundColor: theme.primary },
                ]}
                onPress={() => setTimePeriod('month')}
              >
                <Text
                  style={[
                    styles.periodButtonText,
                    { color: timePeriod === 'month' ? '#FFFFFF' : theme.textSecondary },
                  ]}
                >
                  Month
                </Text>
              </TouchableOpacity>
            </View>
          </View>

          {earningsData && earningsData.length > 0 ? (
            <LineChart
              data={prepareEarningsChartData()}
              width={screenWidth - 60}
              height={220}
              chartConfig={chartConfig}
              bezier
              style={styles.chart}
              withInnerLines={false}
              withOuterLines={true}
              withVerticalLabels={true}
              withHorizontalLabels={true}
              fromZero
            />
          ) : (
            <View style={styles.emptyChart}>
              <Text style={[styles.emptyChartText, { color: theme.textSecondary }]}>
                No earnings data available
              </Text>
            </View>
          )}
        </View>

        {/* Earnings by Category */}
        <View style={[styles.chartCard, { backgroundColor: theme.surface }]}>
          <Text style={[styles.chartTitle, { color: theme.text }]}>Earnings by Category</Text>
          
          {categoryData && categoryData.length > 0 ? (
            <>
              <PieChart
                data={prepareCategoryChartData()}
                width={screenWidth - 60}
                height={220}
                chartConfig={chartConfig}
                accessor="earnings"
                backgroundColor="transparent"
                paddingLeft="15"
                absolute
                style={styles.chart}
              />

              <View style={styles.categoryList}>
                {categoryData.slice(0, 5).map((item: any, index: number) => (
                  <View key={index} style={styles.categoryItem}>
                    <Text style={[styles.categoryName, { color: theme.text }]}>
                      {item.category}
                    </Text>
                    <View style={styles.categoryStats}>
                      <Text style={[styles.categoryEarnings, { color: theme.primary }]}>
                        ${parseFloat(item.earnings || 0).toFixed(0)}
                      </Text>
                      <Text style={[styles.categoryJobs, { color: theme.textSecondary }]}>
                        {item.jobs_count} jobs
                      </Text>
                    </View>
                  </View>
                ))}
              </View>
            </>
          ) : (
            <View style={styles.emptyChart}>
              <Text style={[styles.emptyChartText, { color: theme.textSecondary }]}>
                No category data available
              </Text>
            </View>
          )}
        </View>

        {/* Performance Insights */}
        <View style={[styles.insightsCard, { backgroundColor: theme.surface }]}>
          <Text style={[styles.chartTitle, { color: theme.text }]}>Performance Insights</Text>
          
          <View style={styles.insightItem}>
            <Ionicons name="trending-up" size={24} color="#10B981" />
            <View style={styles.insightContent}>
              <Text style={[styles.insightTitle, { color: theme.text }]}>
                {analytics?.response_rate || 0}% Response Rate
              </Text>
              <Text style={[styles.insightText, { color: theme.textSecondary }]}>
                Keep responding quickly to maintain high visibility
              </Text>
            </View>
          </View>

          <View style={styles.insightItem}>
            <Ionicons name="trophy" size={24} color="#F59E0B" />
            <View style={styles.insightContent}>
              <Text style={[styles.insightTitle, { color: theme.text }]}>
                {calculateSuccessRate()}% Application Success
              </Text>
              <Text style={[styles.insightText, { color: theme.textSecondary }]}>
                {calculateSuccessRate() >= 50 
                  ? 'Great job! Your proposals are winning clients'
                  : 'Improve your proposals to win more jobs'}
              </Text>
            </View>
          </View>

          <View style={styles.insightItem}>
            <Ionicons name="star" size={24} color="#3B82F6" />
            <View style={styles.insightContent}>
              <Text style={[styles.insightTitle, { color: theme.text }]}>
                Profile Completeness
              </Text>
              <Text style={[styles.insightText, { color: theme.textSecondary }]}>
                Complete profiles get 3x more visibility
              </Text>
            </View>
          </View>
        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    gap: 12,
  },
  loadingText: {
    fontSize: 15,
    fontFamily: 'Poppins_400Regular',
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    padding: 20,
    paddingBottom: 40,
  },
  header: {
    marginBottom: 24,
  },
  titleContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  title: {
    fontSize: 28,
    fontFamily: 'Poppins_700Bold',
  },
  metricsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
    marginBottom: 24,
  },
  metricCard: {
    flex: 1,
    minWidth: '47%',
    padding: 20,
    borderRadius: 16,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  metricValue: {
    fontSize: 32,
    fontFamily: 'Poppins_700Bold',
    marginTop: 12,
    marginBottom: 4,
  },
  metricLabel: {
    fontSize: 13,
    fontFamily: 'Poppins_400Regular',
    textAlign: 'center',
  },
  chartCard: {
    padding: 20,
    borderRadius: 16,
    marginBottom: 24,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  chartHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 20,
  },
  chartTitle: {
    fontSize: 18,
    fontFamily: 'Poppins_700Bold',
  },
  periodToggle: {
    flexDirection: 'row',
    gap: 8,
  },
  periodButton: {
    paddingHorizontal: 16,
    paddingVertical: 6,
    borderRadius: 8,
  },
  periodButtonText: {
    fontSize: 13,
    fontFamily: 'Poppins_600SemiBold',
  },
  chart: {
    marginVertical: 8,
    borderRadius: 16,
  },
  emptyChart: {
    height: 220,
    justifyContent: 'center',
    alignItems: 'center',
  },
  emptyChartText: {
    fontSize: 14,
    fontFamily: 'Poppins_400Regular',
  },
  categoryList: {
    marginTop: 20,
    gap: 12,
  },
  categoryItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(0,0,0,0.05)',
  },
  categoryName: {
    fontSize: 15,
    fontFamily: 'Poppins_600SemiBold',
    flex: 1,
  },
  categoryStats: {
    alignItems: 'flex-end',
  },
  categoryEarnings: {
    fontSize: 16,
    fontFamily: 'Poppins_700Bold',
    marginBottom: 2,
  },
  categoryJobs: {
    fontSize: 12,
    fontFamily: 'Poppins_400Regular',
  },
  insightsCard: {
    padding: 20,
    borderRadius: 16,
    marginBottom: 24,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  insightItem: {
    flexDirection: 'row',
    gap: 16,
    marginTop: 20,
  },
  insightContent: {
    flex: 1,
  },
  insightTitle: {
    fontSize: 15,
    fontFamily: 'Poppins_600SemiBold',
    marginBottom: 4,
  },
  insightText: {
    fontSize: 13,
    fontFamily: 'Poppins_400Regular',
    lineHeight: 18,
  },
});
