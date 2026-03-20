import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
  RefreshControl,
  Modal,
  TextInput,
} from 'react-native';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../contexts/ThemeContext';
import apiService from '../../services/api';
import { useTranslation } from 'react-i18next';

interface BankAccount {
  id: string;
  bank_name: string;
  account_holder_name: string;
  account_display: string;
  account_type: string;
  is_verified: boolean;
  is_default: boolean;
  created_at: string;
}

interface MobileMoneyAccount {
  id: string;
  provider: string;
  provider_display: string;
  phone_number: string;
  account_name: string;
  account_display: string;
  is_verified: boolean;
  is_default: boolean;
  created_at: string;
}

export default function PayoutMethodsScreen() {
  const { t } = useTranslation();
  const { theme } = useTheme();
  const [activeTab, setActiveTab] = useState<'bank' | 'mobile'>('bank');
  const [bankAccounts, setBankAccounts] = useState<BankAccount[]>([]);
  const [mobileAccounts, setMobileAccounts] = useState<MobileMoneyAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [showAddModal, setShowAddModal] = useState(false);

  useEffect(() => {
    fetchPayoutMethods();
  }, []);

  const fetchPayoutMethods = async () => {
    try {
      const [bankData, mobileData] = await Promise.all([
        apiService.getBankAccounts().catch(() => []),
        apiService.getMobileMoneyAccounts().catch(() => []),
      ]);

      // Ensure we always have arrays, even if API returns unexpected data
      setBankAccounts(Array.isArray(bankData) ? bankData : []);
      setMobileAccounts(Array.isArray(mobileData) ? mobileData : []);
    } catch (error: any) {
      console.error('Error fetching payout methods:', error);
      // Set empty arrays on error
      setBankAccounts([]);
      setMobileAccounts([]);
      Alert.alert(t('common.error'), 'Failed to load payout methods');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleRefresh = () => {
    setRefreshing(true);
    fetchPayoutMethods();
  };

  const handleSetDefaultBank = async (accountId: string) => {
    try {
      await apiService.setDefaultBankAccount(accountId);
      Alert.alert(t('common.success'), t('payout.defaultPayoutUpdated'));
      fetchPayoutMethods();
    } catch (error) {
      console.error('Error setting default:', error);
      Alert.alert(t('common.error'), t('payout.failedSetDefault'));
    }
  };

  const handleSetDefaultMobile = async (accountId: string) => {
    try {
      await apiService.setDefaultMobileMoneyAccount(accountId);
      Alert.alert(t('common.success'), t('payout.defaultPayoutUpdated'));
      fetchPayoutMethods();
    } catch (error) {
      console.error('Error setting default:', error);
      Alert.alert(t('common.error'), t('payout.failedSetDefault'));
    }
  };

  const handleRemoveBank = async (accountId: string) => {
    Alert.alert(
      'Remove Bank Account?',
      'Are you sure you want to remove this payout method?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Remove',
          style: 'destructive',
          onPress: async () => {
            try {
              await apiService.removeBankAccount(accountId);
              Alert.alert(t('common.success'), t('payout.bankAccountRemoved'));
              fetchPayoutMethods();
            } catch (error) {
              console.error('Error removing bank account:', error);
              Alert.alert(t('common.error'), t('payout.failedRemoveBankAccount'));
            }
          },
        },
      ]
    );
  };

  const handleRemoveMobile = async (accountId: string) => {
    Alert.alert(
      'Remove Mobile Money Account?',
      'Are you sure you want to remove this payout method?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Remove',
          style: 'destructive',
          onPress: async () => {
            try {
              await apiService.removeMobileMoneyAccount(accountId);
              Alert.alert(t('common.success'), t('payout.mobileMoneyRemoved'));
              fetchPayoutMethods();
            } catch (error) {
              console.error('Error removing mobile money account:', error);
              Alert.alert(t('common.error'), t('payout.failedRemoveMobileMoney'));
            }
          },
        },
      ]
    );
  };

  const renderBankAccount = (account: BankAccount) => (
    <View key={account.id} style={[styles.accountCard, { backgroundColor: theme.card }]}>
      <View style={styles.accountHeader}>
        <View style={styles.iconContainer}>
          <Ionicons name="business-outline" size={32} color={theme.primary} />
        </View>
        <View style={styles.accountInfo}>
          <Text style={[styles.accountName, { color: theme.text }]}>{account.bank_name}</Text>
          <Text style={[styles.accountDetail, { color: theme.textSecondary }]}>
            {account.account_display}
          </Text>
          <Text style={[styles.accountDetail, { color: theme.textSecondary }]}>
            {account.account_holder_name}
          </Text>
        </View>
        {account.is_default && (
          <View style={[styles.defaultBadge, { backgroundColor: theme.primary }]}>
            <Text style={styles.defaultBadgeText}>{t('payout.default')}</Text>
          </View>
        )}
      </View>

      {account.is_verified ? (
        <View style={styles.verifiedBadge}>
          <Ionicons name="checkmark-circle" size={16} color="#10B981" />
          <Text style={styles.verifiedText}>{t('payout.verified')}</Text>
        </View>
      ) : (
        <View style={styles.unverifiedBadge}>
          <Ionicons name="time-outline" size={16} color="#F59E0B" />
          <Text style={styles.unverifiedText}>{t('payout.pendingVerification')}</Text>
        </View>
      )}

      <View style={styles.accountActions}>
        {!account.is_default && (
          <TouchableOpacity
            style={[styles.actionButton, { borderColor: theme.primary }]}
            onPress={() => handleSetDefaultBank(account.id)}
          >
            <Text style={[styles.actionButtonText, { color: theme.primary }]}>{t('payout.setAsDefault')}</Text>
          </TouchableOpacity>
        )}
        <TouchableOpacity
          style={[styles.actionButton, styles.removeButton]}
          onPress={() => handleRemoveBank(account.id)}
        >
          <Text style={[styles.actionButtonText, { color: '#EF4444' }]}>{t('payout.remove')}</Text>
        </TouchableOpacity>
      </View>
    </View>
  );

  const renderMobileAccount = (account: MobileMoneyAccount) => (
    <View key={account.id} style={[styles.accountCard, { backgroundColor: theme.card }]}>
      <View style={styles.accountHeader}>
        <View style={styles.iconContainer}>
          <Ionicons name="phone-portrait-outline" size={32} color={theme.primary} />
        </View>
        <View style={styles.accountInfo}>
          <Text style={[styles.accountName, { color: theme.text }]}>
            {account.provider_display}
          </Text>
          <Text style={[styles.accountDetail, { color: theme.textSecondary }]}>
            {account.phone_number}
          </Text>
          <Text style={[styles.accountDetail, { color: theme.textSecondary }]}>
            {account.account_name}
          </Text>
        </View>
        {account.is_default && (
          <View style={[styles.defaultBadge, { backgroundColor: theme.primary }]}>
            <Text style={styles.defaultBadgeText}>{t('payout.default')}</Text>
          </View>
        )}
      </View>

      {account.is_verified ? (
        <View style={styles.verifiedBadge}>
          <Ionicons name="checkmark-circle" size={16} color="#10B981" />
          <Text style={styles.verifiedText}>{t('payout.verified')}</Text>
        </View>
      ) : (
        <View style={styles.unverifiedBadge}>
          <Ionicons name="time-outline" size={16} color="#F59E0B" />
          <Text style={styles.unverifiedText}>{t('payout.pendingVerification')}</Text>
        </View>
      )}

      <View style={styles.accountActions}>
        {!account.is_default && (
          <TouchableOpacity
            style={[styles.actionButton, { borderColor: theme.primary }]}
            onPress={() => handleSetDefaultMobile(account.id)}
          >
            <Text style={[styles.actionButtonText, { color: theme.primary }]}>{t('payout.setAsDefault')}</Text>
          </TouchableOpacity>
        )}
        <TouchableOpacity
          style={[styles.actionButton, styles.removeButton]}
          onPress={() => handleRemoveMobile(account.id)}
        >
          <Text style={[styles.actionButtonText, { color: '#EF4444' }]}>{t('payout.remove')}</Text>
        </TouchableOpacity>
      </View>
    </View>
  );

  if (loading) {
    return (
      <View style={[styles.container, styles.centered, { backgroundColor: theme.background }]}>
        <ActivityIndicator size="large" color={theme.primary} />
      </View>
    );
  }

  const currentAccounts = activeTab === 'bank' ? bankAccounts : mobileAccounts;

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={handleRefresh} />
        }
      >
        <View style={styles.header}>
          <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
            <Ionicons name="arrow-back" size={24} color={theme.text} />
          </TouchableOpacity>
          <Text style={[styles.headerTitle, { color: theme.text }]}>{t('payout.payoutMethods')}</Text>
        </View>

        <View style={styles.tabContainer}>
          <TouchableOpacity
            style={[
              styles.tab,
              activeTab === 'bank' && styles.activeTab,
              { backgroundColor: activeTab === 'bank' ? theme.primary : theme.card },
            ]}
            onPress={() => setActiveTab('bank')}
          >
            <Ionicons
              name="business-outline"
              size={20}
              color={activeTab === 'bank' ? '#FFF' : theme.textSecondary}
            />
            <Text
              style={[
                styles.tabText,
                { color: activeTab === 'bank' ? '#FFF' : theme.textSecondary },
              ]}
            >{t('payout.bankAccount')}</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[
              styles.tab,
              activeTab === 'mobile' && styles.activeTab,
              { backgroundColor: activeTab === 'mobile' ? theme.primary : theme.card },
            ]}
            onPress={() => setActiveTab('mobile')}
          >
            <Ionicons
              name="phone-portrait-outline"
              size={20}
              color={activeTab === 'mobile' ? '#FFF' : theme.textSecondary}
            />
            <Text
              style={[
                styles.tabText,
                { color: activeTab === 'mobile' ? '#FFF' : theme.textSecondary },
              ]}
            >{t('payout.mobileMoney')}</Text>
          </TouchableOpacity>
        </View>

        {currentAccounts.length === 0 ? (
          <View style={styles.emptyState}>
            <Ionicons
              name={activeTab === 'bank' ? 'business-outline' : 'phone-portrait-outline'}
              size={64}
              color={theme.textSecondary}
            />
            <Text style={[styles.emptyTitle, { color: theme.text }]}>
              No {activeTab === 'bank' ? 'Bank Accounts' : 'Mobile Money Accounts'}
            </Text>
            <Text style={[styles.emptySubtitle, { color: theme.textSecondary }]}>{t('payout.addPayoutMethod')}</Text>
          </View>
        ) : (
          <View style={styles.accountsList}>
            {activeTab === 'bank'
              ? (bankAccounts || []).map(renderBankAccount)
              : (mobileAccounts || []).map(renderMobileAccount)}
          </View>
        )}

        <TouchableOpacity
          style={[styles.addButton, { backgroundColor: theme.primary }]}
          onPress={() => Alert.alert(t('profile.comingSoon'), t('payout.addMethodComingSoon'))}
        >
          <Ionicons name="add-circle-outline" size={24} color="#FFF" />
          <Text style={styles.addButtonText}>
            Add {activeTab === 'bank' ? 'Bank Account' : 'Mobile Money'}
          </Text>
        </TouchableOpacity>

        <View style={[styles.infoCard, { backgroundColor: theme.card }]}>
          <Ionicons name="information-circle-outline" size={24} color={theme.primary} />
          <View style={styles.infoContent}>
            <Text style={[styles.infoTitle, { color: theme.text }]}>{t('payout.aboutPayouts')}</Text>
            <Text style={[styles.infoText, { color: theme.textSecondary }]}>{t('nav.earnings')}</Text>
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
  centered: {
    justifyContent: 'center',
    alignItems: 'center',
  },
  scrollContent: {
    padding: 16,
    paddingBottom: 32,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 24,
  },
  backButton: {
    padding: 8,
    marginRight: 8,
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: 'bold',
  },
  tabContainer: {
    flexDirection: 'row',
    gap: 12,
    marginBottom: 24,
  },
  tab: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 12,
    borderRadius: 12,
    gap: 8,
  },
  activeTab: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 2,
  },
  tabText: {
    fontSize: 14,
    fontWeight: '600',
  },
  accountsList: {
    gap: 16,
    marginBottom: 24,
  },
  accountCard: {
    padding: 16,
    borderRadius: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 3,
  },
  accountHeader: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  iconContainer: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: 'rgba(59, 130, 246, 0.1)',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  accountInfo: {
    flex: 1,
  },
  accountName: {
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: 4,
  },
  accountDetail: {
    fontSize: 14,
    marginBottom: 2,
  },
  defaultBadge: {
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 12,
  },
  defaultBadgeText: {
    color: '#FFF',
    fontSize: 12,
    fontWeight: 'bold',
  },
  verifiedBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginBottom: 12,
  },
  verifiedText: {
    color: '#10B981',
    fontSize: 14,
    fontWeight: '600',
  },
  unverifiedBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginBottom: 12,
  },
  unverifiedText: {
    color: '#F59E0B',
    fontSize: 14,
    fontWeight: '600',
  },
  accountActions: {
    flexDirection: 'row',
    gap: 8,
  },
  actionButton: {
    flex: 1,
    padding: 12,
    borderRadius: 8,
    borderWidth: 1,
    alignItems: 'center',
  },
  removeButton: {
    borderColor: '#EF4444',
  },
  actionButtonText: {
    fontSize: 14,
    fontWeight: '600',
  },
  emptyState: {
    alignItems: 'center',
    paddingVertical: 48,
  },
  emptyTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    marginTop: 16,
  },
  emptySubtitle: {
    fontSize: 14,
    marginTop: 8,
    textAlign: 'center',
  },
  addButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 16,
    borderRadius: 12,
    gap: 8,
    marginBottom: 24,
  },
  addButtonText: {
    color: '#FFF',
    fontSize: 16,
    fontWeight: 'bold',
  },
  infoCard: {
    flexDirection: 'row',
    padding: 16,
    borderRadius: 12,
    gap: 12,
  },
  infoContent: {
    flex: 1,
  },
  infoTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: 4,
  },
  infoText: {
    fontSize: 14,
    lineHeight: 20,
  },
});
