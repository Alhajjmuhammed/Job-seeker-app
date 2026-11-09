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
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../contexts/ThemeContext';
import Header from '../../components/Header';
import apiService from '../../services/api';
import { useTranslation } from 'react-i18next';

interface Card {
  id: string;
  // Backend (worker_connect.SavedCardSerializer, GET /v1/payment-methods/cards/)
  // sends card_type/last_four/expiry_month/expiry_year, not
  // brand/last4/exp_month/exp_year. Reading the wrong keys meant every
  // field rendered as "undefined", and card.brand.toUpperCase() in
  // handleRemove() below threw outright since brand was always undefined.
  card_type: string;
  last_four: string;
  expiry_month: number;
  expiry_year: number;
  is_default: boolean;
}

const BRAND_ICON: Record<string, any> = {
  visa: 'card',
  mastercard: 'card',
  amex: 'card',
  default: 'card-outline',
};

export default function ClientPaymentMethods() {
  const { t } = useTranslation();
  const { theme, isDark } = useTheme();
  const [cards, setCards] = useState<Card[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  useEffect(() => {
    loadCards();
  }, []);

  const loadCards = async () => {
    try {
      const data = await apiService.getPaymentMethods();
      setCards(Array.isArray(data) ? data : data?.results || []);
    } catch (e) {
      console.log('payment methods error:', e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const onRefresh = () => {
    setRefreshing(true);
    loadCards();
  };

  const handleSetDefault = async (card: Card) => {
    if (card.is_default) return;
    setActionLoading(card.id);
    try {
      await apiService.setDefaultCard(card.id);
      setCards(prev => prev.map(c => ({ ...c, is_default: c.id === card.id })));
    } catch (e: any) {
      Alert.alert(t('common.error'), e.response?.data?.error || t('paymentMethodsScreen.failedSetDefault'));
    } finally {
      setActionLoading(null);
    }
  };

  const handleRemove = (card: Card) => {
    Alert.alert(
      t('paymentMethodsScreen.removeCard'),
      t('paymentMethodsScreen.removeCardConfirm', { type: card.card_type.toUpperCase(), last4: card.last_four }),
      [
        { text: t('common.cancel'), style: 'cancel' },
        {
          text: t('paymentMethodsScreen.remove'),
          style: 'destructive',
          onPress: async () => {
            setActionLoading(card.id);
            try {
              await apiService.removeCard(card.id);
              setCards(prev => prev.filter(c => c.id !== card.id));
            } catch (e: any) {
              Alert.alert(t('common.error'), e.response?.data?.error || t('paymentMethodsScreen.failedRemove'));
            } finally {
              setActionLoading(null);
            }
          },
        },
      ]
    );
  };

  const s = StyleSheet.create({
    container: { flex: 1, backgroundColor: theme.background },
    scroll: { flex: 1 },
    scrollContent: { padding: 16, paddingBottom: 40 },

    infoCard: {
      flexDirection: 'row', alignItems: 'center', gap: 12,
      backgroundColor: '#EFF6FF', borderRadius: 14,
      padding: 14, marginBottom: 20, borderLeftWidth: 3, borderLeftColor: '#3B82F6',
    },
    infoText: { flex: 1, fontSize: 13, fontFamily: 'Poppins_400Regular', color: '#1e40af', lineHeight: 18 },

    card: {
      backgroundColor: theme.surface, borderRadius: 18, padding: 18, marginBottom: 14,
      shadowColor: '#000', shadowOffset: { width: 0, height: 3 },
      shadowOpacity: 0.08, shadowRadius: 8, elevation: 3,
      borderWidth: 1.5, borderColor: 'transparent',
    },
    cardDefault: { borderColor: theme.primary },
    cardTop: { flexDirection: 'row', alignItems: 'center', marginBottom: 16 },
    cardIconWrap: {
      width: 48, height: 48, borderRadius: 12,
      backgroundColor: '#E6F4F3', alignItems: 'center', justifyContent: 'center',
      marginRight: 14,
    },
    cardBrand: { fontSize: 15, fontFamily: 'Poppins_700Bold', color: theme.text, textTransform: 'capitalize' },
    cardNumber: { fontSize: 13, fontFamily: 'Poppins_400Regular', color: theme.textSecondary, marginTop: 2 },
    defaultBadge: {
      backgroundColor: theme.primary + '20', borderRadius: 8,
      paddingHorizontal: 8, paddingVertical: 3, alignSelf: 'flex-start', marginLeft: 'auto',
    },
    defaultBadgeText: { fontSize: 11, fontFamily: 'Poppins_600SemiBold', color: theme.primary },

    cardBottom: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
    expiry: { fontSize: 13, fontFamily: 'Poppins_400Regular', color: theme.textSecondary },

    actions: { flexDirection: 'row', gap: 8 },
    actionBtn: {
      flexDirection: 'row', alignItems: 'center', gap: 6,
      borderRadius: 10, paddingHorizontal: 12, paddingVertical: 7,
    },
    setDefaultBtn: { backgroundColor: theme.primary + '15', borderWidth: 1, borderColor: theme.primary },
    removeBtn: { backgroundColor: '#FEE2E2', borderWidth: 1, borderColor: '#EF4444' },
    setDefaultText: { fontSize: 12, fontFamily: 'Poppins_600SemiBold', color: theme.primary },
    removeText: { fontSize: 12, fontFamily: 'Poppins_600SemiBold', color: '#EF4444' },

    emptyBox: {
      alignItems: 'center', paddingTop: 60,
    },
    emptyTitle: { fontSize: 16, fontFamily: 'Poppins_600SemiBold', color: theme.text, marginTop: 16 },
    emptySubtitle: {
      fontSize: 13, fontFamily: 'Poppins_400Regular', color: theme.textSecondary,
      marginTop: 8, textAlign: 'center', lineHeight: 20,
    },

    addBtn: {
      backgroundColor: theme.primary, borderRadius: 14,
      flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
      gap: 8, paddingVertical: 15, marginTop: 8,
      shadowColor: theme.primary, shadowOffset: { width: 0, height: 4 },
      shadowOpacity: 0.3, shadowRadius: 8, elevation: 4,
    },
    addBtnText: { fontSize: 16, fontFamily: 'Poppins_600SemiBold', color: '#fff' },

    mobileSection: {
      backgroundColor: theme.surface, borderRadius: 16, padding: 16,
      marginTop: 8,
    },
    mobileSectionTitle: { fontSize: 15, fontFamily: 'Poppins_700Bold', color: theme.text, marginBottom: 12 },
    mobileRow: {
      flexDirection: 'row', alignItems: 'center', gap: 12,
      backgroundColor: isDark ? '#1a2a2a' : '#F0FDF4',
      borderRadius: 12, padding: 12,
    },
    mobileIcon: {
      width: 42, height: 42, borderRadius: 10,
      backgroundColor: '#D1FAE5', alignItems: 'center', justifyContent: 'center',
    },
    mobileName: { fontSize: 14, fontFamily: 'Poppins_600SemiBold', color: theme.text },
    mobileSub: { fontSize: 12, fontFamily: 'Poppins_400Regular', color: theme.textSecondary },
    comingSoonBadge: {
      marginLeft: 'auto', backgroundColor: '#FEF3C7',
      borderRadius: 8, paddingHorizontal: 8, paddingVertical: 3,
    },
    comingSoonText: { fontSize: 10, fontFamily: 'Poppins_600SemiBold', color: '#92400e' },

    loader: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  });

  if (loading) {
    return (
      <View style={[s.container, s.loader]}>
        <ActivityIndicator size="large" color={theme.primary} />
      </View>
    );
  }

  return (
    <View style={s.container}>
      <StatusBar style={isDark ? 'light' : 'dark'} />
      <Header title={t('paymentMethods.paymentMethodsTitle')} />

      <ScrollView
        style={s.scroll}
        contentContainerStyle={s.scrollContent}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={theme.primary} />}
      >
        {/* Info */}
        <View style={s.infoCard}>
          <Ionicons name="shield-checkmark" size={22} color="#3B82F6" />
          <Text style={s.infoText}>
            {t('paymentMethodsScreen.secureInfo')}
          </Text>
        </View>

        {/* Cards */}
        {cards.length === 0 ? (
          <View style={s.emptyBox}>
            <Ionicons name="card-outline" size={60} color={theme.textSecondary} />
            <Text style={s.emptyTitle}>{t('paymentMethods.noPaymentMethods')}</Text>
            <Text style={s.emptySubtitle}>
              {t('paymentMethodsScreen.emptySubtitle')}
            </Text>
          </View>
        ) : (
          cards.map(card => (
            <View key={card.id} style={[s.card, card.is_default && s.cardDefault]}>
              <View style={s.cardTop}>
                <View style={s.cardIconWrap}>
                  <Ionicons name="card" size={26} color={theme.primary} />
                </View>
                <View style={{ flex: 1 }}>
                  <Text style={s.cardBrand}>{card.card_type}</Text>
                  <Text style={s.cardNumber}>•••• •••• •••• {card.last_four}</Text>
                </View>
                {card.is_default && (
                  <View style={s.defaultBadge}>
                    <Text style={s.defaultBadgeText}>{t('paymentMethodsScreen.default')}</Text>
                  </View>
                )}
              </View>

              <View style={s.cardBottom}>
                <Text style={s.expiry}>{t('paymentMethodsScreen.expires', { month: card.expiry_month, year: card.expiry_year })}</Text>
                <View style={s.actions}>
                  {!card.is_default && (
                    <TouchableOpacity
                      style={s.setDefaultBtn}
                      onPress={() => handleSetDefault(card)}
                      disabled={actionLoading === card.id}
                    >
                      {actionLoading === card.id ? (
                        <ActivityIndicator size="small" color={theme.primary} />
                      ) : (
                        <>
                          <Ionicons name="star-outline" size={14} color={theme.primary} />
                          <Text style={s.setDefaultText}>{t('paymentMethodsScreen.setDefault')}</Text>
                        </>
                      )}
                    </TouchableOpacity>
                  )}
                  <TouchableOpacity
                    style={s.removeBtn}
                    onPress={() => handleRemove(card)}
                    disabled={actionLoading === card.id}
                  >
                    <Ionicons name="trash-outline" size={14} color="#EF4444" />
                    <Text style={s.removeText}>{t('paymentMethodsScreen.remove')}</Text>
                  </TouchableOpacity>
                </View>
              </View>
            </View>
          ))
        )}

        {/* Add Card Button */}
        <TouchableOpacity
          style={s.addBtn}
          onPress={() => Alert.alert(t('paymentMethodsScreen.addCard'), t('paymentMethodsScreen.addCardMsg'))}
        >
          <Ionicons name="add-circle-outline" size={22} color="#fff" />
          <Text style={s.addBtnText}>{t('paymentMethodsScreen.addNewCard')}</Text>
        </TouchableOpacity>

        {/* Mobile Money Section */}
        <View style={[s.mobileSection, { marginTop: 24 }]}>
          <Text style={s.mobileSectionTitle}>{t('paymentMethodsScreen.mobileMoney')}</Text>
          {['M-Pesa', 'Airtel Money', 'Tigo Pesa'].map(name => (
            <View key={name} style={[s.mobileRow, { marginBottom: 8 }]}>
              <View style={s.mobileIcon}>
                <Ionicons name="phone-portrait-outline" size={20} color="#10B981" />
              </View>
              <View>
                <Text style={s.mobileName}>{name}</Text>
                <Text style={s.mobileSub}>{t('paymentMethodsScreen.payViaMobile')}</Text>
              </View>
              <View style={s.comingSoonBadge}>
                <Text style={s.comingSoonText}>{t('paymentMethodsScreen.availableAtCheckout')}</Text>
              </View>
            </View>
          ))}
        </View>

      </ScrollView>
    </View>
  );
}
