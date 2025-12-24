import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { router } from 'expo-router';
import { useTheme } from '../../contexts/ThemeContext';
import Header from '../../components/Header';
import apiService from '../../services/api';

interface Transaction {
  id: number;
  amount: number;
  date: string;
  jobTitle: string;
  clientName: string;
  status: 'pending' | 'completed' | 'withdrawn';
}

export default function EarningsScreen() {
  const { theme, isDark } = useTheme();
  const [loading, setLoading] = useState(true);
  const [totalEarnings, setTotalEarnings] = useState(0);
  const [pendingAmount, setPendingAmount] = useState(0);
  const [withdrawnAmount, setWithdrawnAmount] = useState(0);
  const [transactions, setTransactions] = useState<Transaction[]>([]);

  useEffect(() => {
    loadEarningsData();
  }, []);

  const loadEarningsData = async () => {
    try {
      setLoading(true);
      const stats = await apiService.getWorkerStats();
      setTotalEarnings(stats.total_earnings || 0);
      setPendingAmount(stats.pending_earnings || 0);
      setWithdrawnAmount(stats.withdrawn_earnings || 0);
      
      // TODO: Implement getTransactions API endpoint
      // const txns = await apiService.getTransactions();
      // setTransactions(txns);
    } catch (error) {
      console.error('Error loading earnings:', error);
      Alert.alert('Error', 'Failed to load earnings data');
    } finally {
      setLoading(false);
    }
  };

  const handleWithdraw = () => {
    Alert.alert(
      'Withdraw Funds',
      `Available balance: SDG ${pendingAmount.toFixed(2)}`,
      [
        { text: 'Cancel', style: 'cancel' },
        { text: 'Withdraw', onPress: () => Alert.alert('Coming Soon', 'Withdrawal feature coming soon!') },
      ]
    );
  };

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      <StatusBar style={theme.statusBar} />
      
      {/* Header Component */}
      <Header 
        showNotifications 
        showSearch 
        onNotificationPress={() => Alert.alert('Notifications', 'No new notifications')}
        onSearchPress={() => Alert.alert('Search', 'Search coming soon')}
      />

      {loading ? (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#0F766E" />
          <Text style={styles.loadingText}>Loading earnings...</Text>
        </View>
      ) : (
        <ScrollView contentContainerStyle={styles.scrollContent}>
          {/* Balance Cards */}
          <View style={styles.balanceSection}>
            <View style={styles.balanceCard}>
              <Text style={styles.balanceLabel}>Total Earnings</Text>
              <Text style={styles.balanceAmount}>SDG {totalEarnings.toFixed(2)}</Text>
            </View>

            <View style={styles.smallCards}>
              <View style={styles.smallCard}>
                <Text style={styles.smallCardLabel}>Available</Text>
                <Text style={styles.smallCardAmount}>SDG {pendingAmount.toFixed(2)}</Text>
              </View>
              <View style={styles.smallCard}>
                <Text style={styles.smallCardLabel}>Withdrawn</Text>
                <Text style={styles.smallCardAmount}>SDG {withdrawnAmount.toFixed(2)}</Text>
              </View>
            </View>
          </View>

          {/* Withdraw Button */}
          <TouchableOpacity style={styles.withdrawButton} onPress={handleWithdraw}>
            <Text style={styles.withdrawButtonText}>💰 Withdraw Funds</Text>
          </TouchableOpacity>

          {/* Transactions */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Recent Transactions</Text>
            {transactions.length === 0 ? (
              <View style={styles.emptyState}>
                <Text style={styles.emptyIcon}>💸</Text>
                <Text style={styles.emptyText}>No transactions yet</Text>
                <Text style={styles.emptySubtext}>
                  Complete jobs to start earning
                </Text>
              </View>
            ) : (
              transactions.map((txn) => (
                <View key={txn.id} style={styles.transactionCard}>
                  <View style={styles.transactionInfo}>
                    <Text style={styles.transactionTitle}>{txn.jobTitle}</Text>
                    <Text style={styles.transactionClient}>{txn.clientName}</Text>
                    <Text style={styles.transactionDate}>{txn.date}</Text>
                  </View>
                  <View style={styles.transactionRight}>
                    <Text style={styles.transactionAmount}>
                      +SDG {txn.amount.toFixed(2)}
                    </Text>
                    <View style={[styles.statusBadge, getStatusStyle(txn.status)]}>
                      <Text style={styles.statusText}>{txn.status}</Text>
                    </View>
                  </View>
                </View>
              ))
            )}
          </View>
        </ScrollView>
      )}
    </View>
  );
}

function getStatusStyle(status: string) {
  switch (status) {
    case 'completed':
      return { backgroundColor: '#D1FAE5' };
    case 'pending':
      return { backgroundColor: '#FEF3C7' };
    case 'withdrawn':
      return { backgroundColor: '#E0E7FF' };
    default:
      return { backgroundColor: '#F3F4F6' };
  }
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F3F4F6',
  },
  header: {
    backgroundColor: '#0F766E',
    paddingTop: 50,
    paddingBottom: 20,
    paddingHorizontal: 20,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  backButton: {
    width: 40,
  },
  backIcon: {
    fontSize: 28,
    fontFamily: 'Poppins_400Regular',
    color: '#FFFFFF',
  },
  headerTitle: {
    fontSize: 20,
    fontFamily: 'Poppins_700Bold',
    fontWeight: 'bold',
    color: '#FFFFFF',
  },
  headerRight: {
    width: 40,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    marginTop: 12,
    fontSize: 16,
    fontFamily: 'Poppins_400Regular',
    color: '#6B7280',
  },
  scrollContent: {
    padding: 20,
  },
  balanceSection: {
    marginBottom: 20,
  },
  balanceCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 16,
    padding: 24,
    marginBottom: 12,
    elevation: 3,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    alignItems: 'center',
  },
  balanceLabel: {
    fontSize: 14,
    fontFamily: 'Poppins_400Regular',
    color: '#6B7280',
    marginBottom: 8,
  },
  balanceAmount: {
    fontSize: 36,
    fontFamily: 'Poppins_700Bold',
    fontWeight: 'bold',
    color: '#0F766E',
  },
  smallCards: {
    flexDirection: 'row',
    gap: 12,
  },
  smallCard: {
    flex: 1,
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 16,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
  },
  smallCardLabel: {
    fontSize: 12,
    fontFamily: 'Poppins_400Regular',
    color: '#6B7280',
    marginBottom: 4,
  },
  smallCardAmount: {
    fontSize: 18,
    fontFamily: 'Poppins_700Bold',
    fontWeight: '700',
    color: '#1F2937',
  },
  withdrawButton: {
    backgroundColor: '#0F766E',
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
    marginBottom: 24,
  },
  withdrawButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontFamily: 'Poppins_700Bold',
    fontWeight: 'bold',
  },
  section: {
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 18,
    fontFamily: 'Poppins_700Bold',
    fontWeight: 'bold',
    color: '#1F2937',
    marginBottom: 12,
  },
  emptyState: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 40,
    alignItems: 'center',
  },
  emptyIcon: {
    fontSize: 48,
    fontFamily: 'Poppins_400Regular',
    marginBottom: 12,
  },
  emptyText: {
    fontSize: 16,
    fontFamily: 'Poppins_600SemiBold',
    fontWeight: '600',
    color: '#1F2937',
    marginBottom: 4,
  },
  emptySubtext: {
    fontSize: 14,
    fontFamily: 'Poppins_400Regular',
    color: '#6B7280',
  },
  transactionCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    flexDirection: 'row',
    justifyContent: 'space-between',
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
  },
  transactionInfo: {
    flex: 1,
  },
  transactionTitle: {
    fontSize: 16,
    fontFamily: 'Poppins_600SemiBold',
    fontWeight: '600',
    color: '#1F2937',
    marginBottom: 4,
  },
  transactionClient: {
    fontSize: 14,
    fontFamily: 'Poppins_400Regular',
    color: '#6B7280',
    marginBottom: 2,
  },
  transactionDate: {
    fontSize: 12,
    fontFamily: 'Poppins_400Regular',
    color: '#9CA3AF',
  },
  transactionRight: {
    alignItems: 'flex-end',
  },
  transactionAmount: {
    fontSize: 18,
    fontFamily: 'Poppins_700Bold',
    fontWeight: 'bold',
    color: '#059669',
    marginBottom: 4,
  },
  statusBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
  },
  statusText: {
    fontSize: 11,
    fontFamily: 'Poppins_600SemiBold',
    fontWeight: '600',
    color: '#1F2937',
    textTransform: 'capitalize',
  },
});
