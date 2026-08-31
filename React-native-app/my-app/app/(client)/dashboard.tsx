import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  RefreshControl,
  Image,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../contexts/AuthContext';
import { useTheme } from '../../contexts/ThemeContext';
import Header from '../../components/Header';
import apiService from '../../services/api';

interface ServiceRequest {
  id: number;
  title: string;
  status: string;
  urgency: string;
  category_name: string;
  created_at: string;
  total_price?: number;
  worker_name?: string;
}

interface ClientStats {
  total_requests: number;
  active_requests: number;
  completed_requests: number;
  pending_requests: number;
}

const STATUS_COLOR: Record<string, string> = {
  pending: '#F59E0B',
  assigned: '#3B82F6',
  in_progress: '#8B5CF6',
  completed: '#10B981',
  cancelled: '#EF4444',
};

const STATUS_LABEL: Record<string, string> = {
  pending: 'PENDING',
  assigned: 'ASSIGNED',
  in_progress: 'IN PROGRESS',
  completed: 'COMPLETED',
  cancelled: 'CANCELLED',
};

export default function ClientDashboard() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const { theme, isDark } = useTheme();

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [stats, setStats] = useState<ClientStats>({
    total_requests: 0,
    active_requests: 0,
    completed_requests: 0,
    pending_requests: 0,
  });
  const [recentRequests, setRecentRequests] = useState<ServiceRequest[]>([]);

  const loadData = useCallback(async () => {
    try {
      const [statsRes, requestsRes] = await Promise.allSettled([
        apiService.getClientStatistics(),
        apiService.getMyServiceRequests(1),
      ]);

      if (statsRes.status === 'fulfilled') {
        setStats(statsRes.value?.data || statsRes.value || {
          total_requests: 0, active_requests: 0, completed_requests: 0, pending_requests: 0,
        });
      }
      if (requestsRes.status === 'fulfilled') {
        // apiService.getMyServiceRequests() already returns response.data
        // (the paginated {count, results} envelope itself) - value?.data
        // was reading a non-existent nested .data key and always fell
        // through to [], so Recent Requests silently never populated.
        const data = requestsRes.value;
        const results = Array.isArray(data) ? data : data?.results || [];
        setRecentRequests(results.slice(0, 5));
      }
    } catch (error) {
      console.log('Dashboard load error:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const onRefresh = () => {
    setRefreshing(true);
    loadData();
  };

  const s = StyleSheet.create({
    container: { flex: 1, backgroundColor: theme.background },
    scroll: { flex: 1 },

    // ── Hero Banner ──────────────────────────────────────────────
    hero: {
      backgroundColor: '#0D6E68',
      marginHorizontal: 16,
      marginTop: 14,
      borderRadius: 20,
      padding: 20,
      overflow: 'hidden',
      shadowColor: '#0D6E68',
      shadowOffset: { width: 0, height: 6 },
      shadowOpacity: 0.35,
      shadowRadius: 12,
      elevation: 8,
    },
    heroDecor: {
      position: 'absolute', width: 140, height: 140,
      borderRadius: 70, backgroundColor: 'rgba(255,255,255,0.07)',
      top: -40, right: -30,
    },
    heroDecor2: {
      position: 'absolute', width: 80, height: 80,
      borderRadius: 40, backgroundColor: 'rgba(255,255,255,0.05)',
      bottom: -20, left: 100,
    },
    heroTopRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 16 },
    heroLogo: { width: 36, height: 36, borderRadius: 8, marginRight: 10 },
    heroAppName: { fontSize: 16, fontFamily: 'Poppins_700Bold', color: '#fff' },
    heroTagline: { fontSize: 11, fontFamily: 'Poppins_400Regular', color: 'rgba(255,255,255,0.7)' },
    heroGreeting: { fontSize: 13, fontFamily: 'Poppins_400Regular', color: 'rgba(255,255,255,0.8)', marginBottom: 2 },
    heroName: { fontSize: 22, fontFamily: 'Poppins_700Bold', color: '#fff', marginBottom: 16 },
    heroCtaBtn: {
      flexDirection: 'row', alignItems: 'center', gap: 8,
      backgroundColor: '#fff', borderRadius: 12,
      paddingVertical: 10, paddingHorizontal: 16, alignSelf: 'flex-start',
    },
    heroCtaText: { fontSize: 14, fontFamily: 'Poppins_600SemiBold', color: '#0D6E68' },

    // ── Stats ─────────────────────────────────────────────────────
    statsGrid: {
      flexDirection: 'row', flexWrap: 'wrap', gap: 12,
      paddingHorizontal: 16, marginTop: 20,
    },
    statCard: {
      width: '47%', backgroundColor: theme.surface, borderRadius: 16,
      padding: 16,
      shadowColor: '#000', shadowOffset: { width: 0, height: 2 },
      shadowOpacity: 0.06, shadowRadius: 6, elevation: 2,
    },
    statIconWrap: {
      width: 38, height: 38, borderRadius: 10,
      alignItems: 'center', justifyContent: 'center', marginBottom: 10,
    },
    statNum: { fontSize: 26, fontFamily: 'Poppins_700Bold', color: theme.text },
    statLabel: { fontSize: 12, fontFamily: 'Poppins_400Regular', color: theme.textSecondary, marginTop: 2 },

    // ── Quick Actions ─────────────────────────────────────────────
    section: { paddingHorizontal: 16, marginTop: 24 },
    sectionHeader: {
      flexDirection: 'row', justifyContent: 'space-between',
      alignItems: 'center', marginBottom: 14,
    },
    sectionTitle: { fontSize: 16, fontFamily: 'Poppins_700Bold', color: theme.text },
    seeAllText: { fontSize: 13, fontFamily: 'Poppins_500Medium', color: theme.primary },
    actionRow: { flexDirection: 'row', gap: 12 },
    actionCard: {
      flex: 1, borderRadius: 16, padding: 18,
      alignItems: 'center', gap: 10,
      shadowColor: '#000', shadowOffset: { width: 0, height: 2 },
      shadowOpacity: 0.08, shadowRadius: 6, elevation: 3,
    },
    actionIcon: {
      width: 48, height: 48, borderRadius: 14,
      alignItems: 'center', justifyContent: 'center',
    },
    actionCardTitle: { fontSize: 13, fontFamily: 'Poppins_600SemiBold', textAlign: 'center' },
    actionCardSub: { fontSize: 11, fontFamily: 'Poppins_400Regular', textAlign: 'center', opacity: 0.75 },

    // ── Recent Requests ───────────────────────────────────────────
    listCard: {
      backgroundColor: theme.surface, borderRadius: 16,
      overflow: 'hidden',
      shadowColor: '#000', shadowOffset: { width: 0, height: 2 },
      shadowOpacity: 0.06, shadowRadius: 6, elevation: 2,
    },
    listItem: {
      flexDirection: 'row', alignItems: 'center',
      paddingHorizontal: 16, paddingVertical: 14,
    },
    listItemLeft: {
      width: 42, height: 42, borderRadius: 12,
      alignItems: 'center', justifyContent: 'center', marginRight: 12,
    },
    listItemBody: { flex: 1 },
    listItemTitle: { fontSize: 14, fontFamily: 'Poppins_600SemiBold', color: theme.text, marginBottom: 3 },
    listItemMeta: { fontSize: 12, fontFamily: 'Poppins_400Regular', color: theme.textSecondary },
    listItemBadge: {
      borderRadius: 8, paddingHorizontal: 8, paddingVertical: 3, marginLeft: 8,
    },
    listItemBadgeText: { fontSize: 10, fontFamily: 'Poppins_600SemiBold', color: '#fff' },
    listDivider: { height: 1, backgroundColor: theme.border || (isDark ? '#2a2a2a' : '#f0f0f0'), marginLeft: 70 },

    // ── Empty / Loader ────────────────────────────────────────────
    emptyBox: {
      backgroundColor: theme.surface, borderRadius: 16, padding: 36, alignItems: 'center',
    },
    emptyText: {
      fontSize: 14, fontFamily: 'Poppins_400Regular',
      color: theme.textSecondary, marginTop: 12, textAlign: 'center', lineHeight: 22,
    },
    centerLoader: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: theme.background },
    bottomPad: { height: 32 },
  });

  if (loading) {
    return (
      <View style={s.centerLoader}>
        <ActivityIndicator size="large" color={theme.primary} />
      </View>
    );
  }

  const STATS = [
    { label: 'Total Requests', value: stats.total_requests, color: '#0D6E68', bg: '#E6F4F3', icon: 'list-outline' as const },
    { label: 'Active', value: stats.active_requests, color: '#3B82F6', bg: '#EFF6FF', icon: 'flash-outline' as const },
    { label: 'Completed', value: stats.completed_requests, color: '#10B981', bg: '#ECFDF5', icon: 'checkmark-circle-outline' as const },
    { label: 'Pending', value: stats.pending_requests, color: '#F59E0B', bg: '#FFFBEB', icon: 'time-outline' as const },
  ];

  return (
    <View style={s.container}>
      <StatusBar style={isDark ? 'light' : 'dark'} />
      <Header title="Worker Connect" />
      <ScrollView
        style={s.scroll}
        showsVerticalScrollIndicator={false}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={theme.primary} />}
      >
        {/* ── Hero Banner ── */}
        <View style={s.hero}>
          <View style={s.heroDecor} />
          <View style={s.heroDecor2} />
          <View style={s.heroTopRow}>
            <Image source={require('../../assets/images/logo.png')} style={s.heroLogo} resizeMode="contain" />
            <View>
              <Text style={s.heroAppName}>Worker Connect</Text>
              <Text style={s.heroTagline}>Services at your fingertips</Text>
            </View>
          </View>
          <Text style={s.heroGreeting}>Hello, {user?.firstName || 'there'} 👋</Text>
          <Text style={s.heroName}>What do you need{'\n'}help with today?</Text>
          <TouchableOpacity style={s.heroCtaBtn} onPress={() => router.push('/(client)/request-service')}>
            <Ionicons name="add-circle" size={18} color="#0D6E68" />
            <Text style={s.heroCtaText}>New Request</Text>
          </TouchableOpacity>
        </View>

        {/* ── Stats Grid ── */}
        <View style={s.statsGrid}>
          {STATS.map((st) => (
            <View key={st.label} style={s.statCard}>
              <View style={[s.statIconWrap, { backgroundColor: st.bg }]}>
                <Ionicons name={st.icon} size={20} color={st.color} />
              </View>
              <Text style={[s.statNum, { color: st.color }]}>{st.value}</Text>
              <Text style={s.statLabel}>{st.label}</Text>
            </View>
          ))}
        </View>

        {/* ── Quick Actions ── */}
        <View style={s.section}>
          <View style={s.sectionHeader}>
            <Text style={s.sectionTitle}>Quick Actions</Text>
          </View>
          <View style={s.actionRow}>
            <TouchableOpacity
              style={[s.actionCard, { backgroundColor: '#0D6E68' }]}
              onPress={() => router.push('/(client)/request-service')}
            >
              <View style={[s.actionIcon, { backgroundColor: 'rgba(255,255,255,0.15)' }]}>
                <Ionicons name="add-circle-outline" size={26} color="#fff" />
              </View>
              <Text style={[s.actionCardTitle, { color: '#fff' }]}>Request{'\n'}Service</Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={[s.actionCard, { backgroundColor: theme.surface, borderWidth: 1.5, borderColor: theme.primary }]}
              onPress={() => router.push('/(client)/my-requests')}
            >
              <View style={[s.actionIcon, { backgroundColor: '#E6F4F3' }]}>
                <Ionicons name="document-text-outline" size={26} color="#0D6E68" />
              </View>
              <Text style={[s.actionCardTitle, { color: theme.text }]}>My{'\n'}Requests</Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={[s.actionCard, { backgroundColor: theme.surface, borderWidth: 1.5, borderColor: '#3B82F6' }]}
              onPress={() => router.push('/(client)/search')}
            >
              <View style={[s.actionIcon, { backgroundColor: '#EFF6FF' }]}>
                <Ionicons name="search-outline" size={26} color="#3B82F6" />
              </View>
              <Text style={[s.actionCardTitle, { color: theme.text }]}>Browse{'\n'}Services</Text>
            </TouchableOpacity>
          </View>
        </View>

        {/* ── Recent Requests ── */}
        <View style={[s.section, { marginBottom: 32 }]}>
          <View style={s.sectionHeader}>
            <Text style={s.sectionTitle}>Recent Requests</Text>
            <TouchableOpacity onPress={() => router.push('/(client)/my-requests')}>
              <Text style={s.seeAllText}>See All</Text>
            </TouchableOpacity>
          </View>

          {recentRequests.length === 0 ? (
            <View style={s.emptyBox}>
              <Ionicons name="clipboard-outline" size={44} color={theme.textSecondary} />
              <Text style={s.emptyText}>
                No service requests yet.{'\n'}Tap &quot;New Request&quot; to get started.
              </Text>
            </View>
          ) : (
            <View style={s.listCard}>
              {recentRequests.map((req, index) => {
                const color = STATUS_COLOR[req.status] || '#9CA3AF';
                return (
                  <View key={req.id}>
                    <TouchableOpacity
                      style={s.listItem}
                      onPress={() => router.push(`/(client)/service-request/${req.id}`)}
                      activeOpacity={0.7}
                    >
                      <View style={[s.listItemLeft, { backgroundColor: color + '20' }]}>
                        <Ionicons name="construct-outline" size={20} color={color} />
                      </View>
                      <View style={s.listItemBody}>
                        <Text style={s.listItemTitle} numberOfLines={1}>
                          {req.title || req.category_name}
                        </Text>
                        <Text style={s.listItemMeta}>
                          {req.category_name}
                          {req.worker_name ? `  ·  ${req.worker_name}` : ''}
                          {'  ·  '}{new Date(req.created_at).toLocaleDateString()}
                        </Text>
                      </View>
                      <View style={[s.listItemBadge, { backgroundColor: color }]}>
                        <Text style={s.listItemBadgeText}>{STATUS_LABEL[req.status] || req.status}</Text>
                      </View>
                      <Ionicons name="chevron-forward" size={16} color={theme.textSecondary} style={{ marginLeft: 6 }} />
                    </TouchableOpacity>
                    {index < recentRequests.length - 1 && <View style={s.listDivider} />}
                  </View>
                );
              })}
            </View>
          )}
        </View>

        <View style={s.bottomPad} />
      </ScrollView>
    </View>
  );
}
