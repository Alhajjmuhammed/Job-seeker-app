import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  RefreshControl,
  Dimensions,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { LineChart } from 'react-native-chart-kit';
import { useTheme } from '../../contexts/ThemeContext';
import Header from '../../components/Header';
import apiService from '../../services/api';

const screenWidth = Dimensions.get('window').width;

interface Transaction {
  id: number;
  job_id: number;
  job_title: string;
  client_name: string;
  amount: string;
  date: string;
  status: string;
}

export default function EarningsScreen() {
  const { theme, isDark } = useTheme();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [totalEarnings, setTotalEarnings] = useState(0);
  const [pendingAmount, setPendingAmount] = useState(0);
  const [withdrawnAmount, setWithdrawnAmount] = useState(0);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [earningsData, setEarningsData] = useState<any>(null);
  const [topClients, setTopClients] = useState<any[]>([]);

  useEffect(() => {
    loadEarningsData();
  }, []);

  const loadEarningsData = async () => {
    try {
      setLoading(true);
      
      const [stats, paymentHistory, earningsBreakdown, clientsData] = await Promise.all([
        apiService.getWorkerStats().catch(() => ({ total_earnings: 0 })),
        apiService.getPaymentHistory(20).catch(() => []),
        apiService.getEarningsBreakdown('month', 6).catch(() => []),
        apiService.getTopClients(5).catch(() => []),
      ]);

      setTotalEarnings(stats.total_earnings || 0);
      setPendingAmount(stats.pending_earnings || 0);
      setWithdrawnAmount(stats.withdrawn_earnings || 0);
      setTransactions(paymentHistory || []);
      setEarningsData(earningsBreakdown || []);
      setTopClients(clientsData || []);
    } catch (error) {
      console.error('Error loading earnings:', error);
    } finally {
      setLoading(false);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await loadEarningsData();
    setRefreshing(false);
  };

  const handleWithdraw = () => {
    Alert.alert(
      'Withdraw Funds',
      `Available balance: $${(Number(pendingAmount) || 0).toFixed(2)}`,
      [
        { text: 'Cancel', style: 'cancel' },
        { text: 'Withdraw', onPress: () => Alert.alert('Coming Soon', 'Withdrawal feature coming soon!') },
      ]
    );
  };

  const prepareChartData = () => {
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
      r: '4',
      strokeWidth: '2',
      stroke: theme.primary,
    },
  };

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      <StatusBar style={theme.statusBar} />
      <Header showBack />

      {loading ? (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={theme.primary} />
          <Text style={[styles.loadingText, { color: theme.textSecondary }]}>Loading earnings...</Text>
        </View>
      ) : (
        <ScrollView 
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
          {/* Balance Cards */}
          <View style={styles.balanceSection}>
            <View style={[styles.balanceCard, { backgroundColor: theme.surface }]}>
              <Ionicons name="wallet" size={32} color={theme.primary} style={{ marginBottom: 8 }} />
              <Text style={[styles.balanceLabel, { color: theme.textSecondary }]}>Total Earnings</Text>
              <Text style={[styles.balanceAmount, { color: theme.primary }]}>
                ${(Number(totalEarnings) || 0).toFixed(2)}
              </Text>
            </View>

            <View style={styles.smallCards}>
              <View style={[styles.smallCard, { backgroundColor: theme.surface }]}>
                <Ionicons name="cash" size={24} color="#10B981" style={{ marginBottom: 4 }} />
                <Text style={[styles.smallCardLabel, { color: theme.textSecondary }]}>Available</Text>
                <Text style={[styles.smallCardAmount, { color: theme.text }]}>
                  ${(Number(pendingAmount) || 0).toFixed(2)}
                </Text>
              </View>
              <View style={[styles.smallCard, { backgroundColor: theme.surface }]}>
                <Ionicons name="card" size={24} color="#3B82F6" style={{ marginBottom: 4 }} />
                <Text style={[styles.smallCardLabel, { color: theme.textSecondary }]}>Withdrawn</Text>
                <Text style={[styles.smallCardAmount, { color: theme.text }]}>
                  ${(Number(withdrawnAmount) || 0).toFixed(2)}
                </Text>
              </View>
            </View>
          </View>

          {/* Withdraw Button */}
          <TouchableOpacity 
            style={[styles.withdrawButton, { backgroundColor: theme.primary }]} 
            onPress={handleWithdraw}
          >
            <Ionicons name="download-outline" size={20} color="#FFFFFF" />
            <Text style={styles.withdrawButtonText}>Withdraw Funds</Text>
          </TouchableOpacity>

          {/* Earnings Chart */}
          {earningsData && earningsData.length > 0 && (
            <View style={[styles.chartCard, { backgroundColor: theme.surface }]}>
              <Text style={[styles.sectionTitle, { color: theme.text }]}>Earnings Trend</Text>
              <LineChart
                data={prepareChartData()}
                width={screenWidth - 60}
                height={200}
                chartConfig={chartConfig}
                bezier
                style={styles.chart}
                withInnerLines={false}
                withOuterLines={true}
                fromZero
              />
            </View>
          )}

          {/* Top Clients */}
          {topClients.length > 0 && (
            <View style={styles.section}>
              <Text style={[styles.sectionTitle, { color: theme.text }]}>Top Clients</Text>
              {topClients.map((client: any, index: number) => (
                <View key={index} style={[styles.clientCard, { backgroundColor: theme.surface }]}>
                  <View style={styles.clientInfo}>
                    <Ionicons name="person-circle" size={40} color={theme.primary} />
                    <View style={styles.clientDetails}>
                      <Text style={[styles.clientName, { color: theme.text }]}>
                        {client.client_name}
                      </Text>
                      <Text style={[styles.clientJobs, { color: theme.textSecondary }]}>
                        {client.jobs_count} {client.jobs_count === 1 ? 'job' : 'jobs'}
                      </Text>
                    </View>
                  </View>
                  <Text style={[styles.clientEarnings, { color: theme.primary }]}>
                    ${parseFloat(client.total_earnings || 0).toFixed(0)}
                  </Text>
                </View>
              ))}
            </View>
          )}

          {/* Transactions */}
          <View style={styles.section}>
            <Text style={[styles.sectionTitle, { color: theme.text }]}>Recent Payments</Text>
            {transactions.length === 0 ? (
              <View style={[styles.emptyState, { backgroundColor: theme.surface }]}>
                <Ionicons name="receipt-outline" size={56} color={theme.textSecondary} />
                <Text style={[styles.emptyText, { color: theme.text }]}>No payments yet</Text>
                <Text style={[styles.emptySubtext, { color: theme.textSecondary }]}>
                  Complete jobs to start earning
                </Text>
              </View>
            ) : (
              transactions.map((txn) => (
                <TouchableOpacity
                  key={txn.id}
                  style={[styles.transactionCard, { backgroundColor: theme.surface }]}
                  onPress={() => router.push(`/job/${txn.job_id}` as any)}
                >
                  <View style={styles.transactionInfo}>
                    <Text style={[styles.transactionTitle, { color: theme.text }]}>
                      {txn.job_title}
                    </Text>
                    <Text style={[styles.transactionClient, { color: theme.textSecondary }]}>
                      {txn.client_name}
                    </Text>
                    <Text style={[styles.transactionDate, { color: theme.textSecondary }]}>
                      {new Date(txn.date).toLocaleDateString()}
                    </Text>
                  </View>
                  <View style={styles.transactionRight}>
                    <Text style={[styles.transactionAmount, { color: '#10B981' }]}>
                      +${parseFloat(String(txn.amount || 0)).toFixed(2)}
                    </Text>
                    <Ionicons name="chevron-forward" size={20} color={theme.textSecondary} />
                  </View>
                </TouchableOpacity>
              ))
            )}
          </View>
        </ScrollView>
      )}
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
  scrollContent: {
    padding: 20,
    paddingBottom: 40,
  },
  balanceSection: {
    marginBottom: 20,
  },
  balanceCard: {
    padding: 24,
    borderRadius: 20,
    marginBottom: 16,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 5,
  },
  balanceLabel: {
    fontSize: 14,
    fontFamily: 'Poppins_400Regular',
    marginBottom: 8,
  },
  balanceAmount: {
    fontSize: 40,
    fontFamily: 'Poppins_700Bold',
  },
  smallCards: {
    flexDirection: 'row',
    gap: 16,
  },
  smallCard: {
    flex: 1,
    padding: 16,
    borderRadius: 16,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  smallCardLabel: {
    fontSize: 12,
    fontFamily: 'Poppins_400Regular',
    marginBottom: 4,
  },
  smallCardAmount: {
    fontSize: 18,
    fontFamily: 'Poppins_700Bold',
  },
  withdrawButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    paddingVertical: 14,
    borderRadius: 12,
    marginBottom: 24,
  },
  withdrawButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontFamily: 'Poppins_600SemiBold',
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
  chart: {
    marginVertical: 8,
    borderRadius: 16,
  },
  section: {
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 20,
    fontFamily: 'Poppins_700Bold',
    marginBottom: 16,
  },
  clientCard: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    borderRadius: 12,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 3,
    elevation: 2,
  },
  clientInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    flex: 1,
  },
  clientDetails: {
    flex: 1,
  },
  clientName: {
    fontSize: 16,
    fontFamily: 'Poppins_600SemiBold',
    marginBottom: 2,
  },
  clientJobs: {
    fontSize: 13,
    fontFamily: 'Poppins_400Regular',
  },
  clientEarnings: {
    fontSize: 18,
    fontFamily: 'Poppins_700Bold',
  },
  emptyState: {
    alignItems: 'center',
    padding: 40,
    borderRadius: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 3,
    elevation: 2,
  },
  emptyText: {
    fontSize: 18,
    fontFamily: 'Poppins_600SemiBold',
    marginTop: 16,
    marginBottom: 8,
  },
  emptySubtext: {
    fontSize: 14,
    fontFamily: 'Poppins_400Regular',
    textAlign: 'center',
  },
  transactionCard: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    borderRadius: 12,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 3,
    elevation: 2,
  },
  transactionInfo: {
    flex: 1,
    paddingRight: 16,
  },
  transactionTitle: {
    fontSize: 15,
    fontFamily: 'Poppins_600SemiBold',
    marginBottom: 4,
  },
  transactionClient: {
    fontSize: 13,
    fontFamily: 'Poppins_400Regular',
    marginBottom: 2,
  },
  transactionDate: {
    fontSize: 12,
    fontFamily: 'Poppins_400Regular',
  },
  transactionRight: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  transactionAmount: {
    fontSize: 16,
    fontFamily: 'Poppins_700Bold',
  },
});
