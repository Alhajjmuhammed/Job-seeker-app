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
} from 'react-native';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../contexts/ThemeContext';
import apiService from '../../services/api';
import { useTranslation } from 'react-i18next';

interface SavedCard {
  id: string;
  card_type: string;
  last_four: string;
  expiry_month: number;
  expiry_year: number;
  cardholder_name: string;
  card_display: string;
  is_default: boolean;
  is_expired: boolean;
  created_at: string;
}

export default function PaymentMethodsScreen() {
  const { t } = useTranslation();
  const { theme } = useTheme();
  const [cards, setCards] = useState<SavedCard[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    fetchPaymentMethods();
  }, []);

  const fetchPaymentMethods = async () => {
    try {
      const data = await apiService.getPaymentMethods();
      // Ensure we always have an array, even if API returns unexpected data
      setCards(Array.isArray(data) ? data : []);
    } catch (error: any) {
      console.error('Error fetching payment methods:', error);
      // Set empty array on error
      setCards([]);
      if (error.response?.status !== 404) {
        Alert.alert(t('common.error'), t('paymentMethods.failedLoadPaymentMethods'));
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleRefresh = () => {
    setRefreshing(true);
    fetchPaymentMethods();
  };

  const handleSetDefault = async (cardId: string) => {
    try {
      await apiService.setDefaultCard(cardId);
      Alert.alert(t('common.success'), t('paymentMethods.defaultPaymentUpdated'));
      fetchPaymentMethods();
    } catch (error) {
      console.error('Error setting default:', error);
      Alert.alert(t('common.error'), t('paymentMethods.failedSetDefaultPayment'));
    }
  };

  const handleRemoveCard = async (cardId: string) => {
    Alert.alert(
      'Remove Card?',
      'Are you sure you want to remove this payment method?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Remove',
          style: 'destructive',
          onPress: async () => {
            try {
              await apiService.removeCard(cardId);
              Alert.alert(t('common.success'), t('paymentMethods.paymentMethodRemoved'));
              fetchPaymentMethods();
            } catch (error) {
              console.error('Error removing card:', error);
              Alert.alert(t('common.error'), t('paymentMethods.failedRemovePaymentMethod'));
            }
          },
        },
      ]
    );
  };

  const getCardIcon = (cardType: string) => {
    switch (cardType.toLowerCase()) {
      case 'visa':
        return 'card';
      case 'mastercard':
        return 'card';
      case 'amex':
        return 'card';
      default:
        return 'card-outline';
    }
  };

  const getCardColor = (cardType: string) => {
    switch (cardType.toLowerCase()) {
      case 'visa':
        return ['#1A1F71', '#0066CC'];
      case 'mastercard':
        return ['#EB001B', '#FF5F00'];
      case 'amex':
        return ['#006FCF', '#00A3E0'];
      default:
        return ['#4A5568', '#718096'];
    }
  };

  const renderCardItem = (card: SavedCard) => (
    <View key={card.id} style={[styles.cardContainer, { backgroundColor: theme.card }]}>
      <View
        style={[styles.cardGradient, { backgroundColor: getCardColor(card.card_type)[0] }]}
      >
        <View style={styles.cardHeader}>
          <View style={styles.cardTypeContainer}>
            <Ionicons name={getCardIcon(card.card_type) as any} size={32} color="#FFF" />
            <Text style={styles.cardTypeName}>{card.card_type.toUpperCase()}</Text>
          </View>
          {card.is_default && (
            <View style={styles.defaultBadge}>
              <Text style={styles.defaultBadgeText}>{t('payout.default')}</Text>
            </View>
          )}
        </View>

        <Text style={styles.cardNumber}>•••• •••• •••• {card.last_four}</Text>
        
        <View style={styles.cardFooter}>
          <View>
            <Text style={styles.cardLabel}>{t('paymentMethods.cardHolder')}</Text>
            <Text style={styles.cardHolder}>{card.cardholder_name}</Text>
          </View>
          <View>
            <Text style={styles.cardLabel}>{t('paymentMethods.expires')}</Text>
            <Text style={[styles.cardExpiry, card.is_expired && styles.cardExpired]}>
              {String(card.expiry_month).padStart(2, '0')}/{card.expiry_year}
            </Text>
          </View>
        </View>
      </View>

      <View style={styles.cardActions}>
        {!card.is_default && (
          <TouchableOpacity
            style={[styles.actionButton, { borderColor: theme.primary }]}
            onPress={() => handleSetDefault(card.id)}
          >
            <Ionicons name="checkmark-circle-outline" size={20} color={theme.primary} />
            <Text style={[styles.actionButtonText, { color: theme.primary }]}>{t('payout.setAsDefault')}</Text>
          </TouchableOpacity>
        )}
        <TouchableOpacity
          style={[styles.actionButton, styles.removeButton]}
          onPress={() => handleRemoveCard(card.id)}
        >
          <Ionicons name="trash-outline" size={20} color="#EF4444" />
          <Text style={[styles.actionButtonText, { color: '#EF4444' }]}>{t('payout.remove')}</Text>
        </TouchableOpacity>
      </View>

      {card.is_expired && (
        <View style={styles.expiredWarning}>
          <Ionicons name="warning-outline" size={18} color="#F59E0B" />
          <Text style={styles.expiredWarningText}>{t('paymentMethods.cardExpired')}</Text>
        </View>
      )}
    </View>
  );

  if (loading) {
    return (
      <View style={[styles.container, styles.centered, { backgroundColor: theme.background }]}>
        <ActivityIndicator size="large" color={theme.primary} />
      </View>
    );
  }

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
          <Text style={[styles.headerTitle, { color: theme.text }]}>{t('paymentMethods.paymentMethodsTitle')}</Text>
        </View>

        {cards.length === 0 ? (
          <View style={styles.emptyState}>
            <Ionicons name="card-outline" size={64} color={theme.textSecondary} />
            <Text style={[styles.emptyTitle, { color: theme.text }]}>{t('paymentMethods.noPaymentMethods')}</Text>
            <Text style={[styles.emptySubtitle, { color: theme.textSecondary }]}>{t('paymentMethods.addPaymentMethodMessage')}</Text>
          </View>
        ) : (
          <View style={styles.cardsList}>
            {(cards || []).map(renderCardItem)}
          </View>
        )}

        <TouchableOpacity
          style={[styles.addButton, { backgroundColor: theme.primary }]}
          onPress={() => Alert.alert(t('profile.comingSoon'), t('paymentMethods.addPaymentMethodComingSoon'))}
        >
          <Ionicons name="add-circle-outline" size={24} color="#FFF" />
          <Text style={styles.addButtonText}>{t('paymentMethods.addPaymentMethod')}</Text>
        </TouchableOpacity>

        <View style={[styles.infoCard, { backgroundColor: theme.card }]}>
          <Ionicons name="shield-checkmark-outline" size={24} color={theme.primary} />
          <View style={styles.infoContent}>
            <Text style={[styles.infoTitle, { color: theme.text }]}>{t('paymentMethods.securePayments')}</Text>
            <Text style={[styles.infoText, { color: theme.textSecondary }]}>{t('paymentMethods.securePaymentsMessage')}</Text>
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
  cardsList: {
    gap: 16,
    marginBottom: 24,
  },
  cardContainer: {
    borderRadius: 12,
    overflow: 'hidden',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 3,
  },
  cardGradient: {
    padding: 20,
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 24,
  },
  cardTypeContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  cardTypeName: {
    color: '#FFF',
    fontSize: 16,
    fontWeight: 'bold',
  },
  defaultBadge: {
    backgroundColor: 'rgba(255, 255, 255, 0.3)',
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 12,
  },
  defaultBadgeText: {
    color: '#FFF',
    fontSize: 12,
    fontWeight: 'bold',
  },
  cardNumber: {
    color: '#FFF',
    fontSize: 20,
    fontWeight: '600',
    letterSpacing: 2,
    marginBottom: 20,
  },
  cardFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  cardLabel: {
    color: 'rgba(255, 255, 255, 0.7)',
    fontSize: 10,
    marginBottom: 4,
  },
  cardHolder: {
    color: '#FFF',
    fontSize: 14,
    fontWeight: '600',
  },
  cardExpiry: {
    color: '#FFF',
    fontSize: 14,
    fontWeight: '600',
  },
  cardExpired: {
    color: '#F59E0B',
  },
  cardActions: {
    flexDirection: 'row',
    padding: 12,
    gap: 8,
  },
  actionButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 12,
    borderRadius: 8,
    borderWidth: 1,
    gap: 6,
  },
  removeButton: {
    borderColor: '#EF4444',
  },
  actionButtonText: {
    fontSize: 14,
    fontWeight: '600',
  },
  expiredWarning: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 12,
    backgroundColor: '#FEF3C7',
    gap: 8,
  },
  expiredWarningText: {
    color: '#92400E',
    fontSize: 14,
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
