import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  Image,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { router, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../contexts/ThemeContext';
import Header from '../../components/Header';
import apiService from '../../services/api';
import { useTranslation } from 'react-i18next';

interface BrowseWorker {
  id: number;
  name: string;
  profile_image: string | null;
  bio: string;
  average_rating: string;
  completed_jobs: number;
  experience_years: number;
  city: string;
  distance_km: number | null;
  categories: { id: number; name: string }[];
  /** verified + ID uploaded: may be booked directly (older servers don't send it) */
  can_direct_hire?: boolean;
}

export default function ChooseWorkerScreen() {
  const { theme } = useTheme();
  const { t } = useTranslation();
  const params = useLocalSearchParams<{ categoryId: string; latitude?: string; longitude?: string }>();
  const [loading, setLoading] = useState(true);
  const [workers, setWorkers] = useState<BrowseWorker[]>([]);

  // Reload when the client comes back with a different category or location.
  useEffect(() => {
    loadWorkers();
  }, [params.categoryId, params.latitude, params.longitude]);

  const loadWorkers = async () => {
    try {
      setLoading(true);
      const categoryId = Number(params.categoryId);
      const lat = params.latitude ? Number(params.latitude) : null;
      const lon = params.longitude ? Number(params.longitude) : null;
      const data = await apiService.getAvailableWorkersForRequest(categoryId, lat, lon);
      setWorkers(data.workers || []);
    } catch (error) {
      console.error('Failed to load workers:', error);
      Alert.alert(t('common.error'), t('jobsBoard.failedLoadWorkers'));
    } finally {
      setLoading(false);
    }
  };

  const handleSelect = (worker: BrowseWorker) => {
    router.push({
      pathname: '/(client)/request-service',
      params: { preferredWorkerId: worker.id.toString(), preferredWorkerName: worker.name },
    });
  };

  const handleBookDirectly = (worker: BrowseWorker) => {
    router.push({
      pathname: '/(client)/direct-hire/new' as any,
      params: { workerId: worker.id.toString(), workerName: worker.name },
    });
  };

  const handleSkip = () => {
    router.back();
  };

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      <StatusBar style={theme.statusBar} />
      <Header showBack />

      <View style={styles.header}>
        <Text style={[styles.title, { color: theme.text }]}>{t('jobsBoard.chooseWorker')}</Text>
        <Text style={[styles.subtitle, { color: theme.textSecondary }]}>
          {t('jobsBoard.chooseWorkerHint')}
        </Text>
      </View>

      {loading ? (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={theme.primary} />
        </View>
      ) : (
        <ScrollView contentContainerStyle={styles.scrollContent}>
          {workers.length === 0 ? (
            <View style={styles.emptyState}>
              <Ionicons name="people-outline" size={56} color={theme.textSecondary} style={{ marginBottom: 16 }} />
              <Text style={[styles.emptyTitle, { color: theme.text }]}>{t('jobsBoard.noWorkersNow')}</Text>
              <Text style={[styles.emptySubtitle, { color: theme.textSecondary }]}>
                {t('jobsBoard.noWorkersNowHint')}
              </Text>
            </View>
          ) : (
            workers.map((worker) => (
              <View key={worker.id} style={[styles.cardWrap, { backgroundColor: theme.surface, borderColor: theme.border }]}>
              <TouchableOpacity
                style={styles.card}
                onPress={() => handleSelect(worker)}
              >
                {worker.profile_image ? (
                  <Image source={{ uri: worker.profile_image }} style={styles.avatar} />
                ) : (
                  <View style={[styles.avatarPlaceholder, { backgroundColor: theme.primary }]}>
                    <Text style={styles.avatarInitial}>{worker.name.charAt(0).toUpperCase()}</Text>
                  </View>
                )}
                <View style={styles.cardBody}>
                  <Text style={[styles.name, { color: theme.text }]}>{worker.name}</Text>
                  <View style={styles.metaRow}>
                    <Ionicons name="star" size={14} color="#FBBF24" />
                    <Text style={[styles.metaText, { color: theme.textSecondary }]}>
                      {t('jobsBoard.workerMeta', { rating: worker.average_rating, jobs: worker.completed_jobs, years: worker.experience_years })}
                    </Text>
                  </View>
                  <View style={styles.metaRow}>
                    <Ionicons name="location-outline" size={14} color={theme.textSecondary} />
                    <Text style={[styles.metaText, { color: theme.textSecondary }]}>
                      {worker.city || t('jobsBoard.unknownCity')}
                      {worker.distance_km !== null ? t('jobsBoard.kmAway', { km: worker.distance_km }) : ''}
                    </Text>
                  </View>
                  {worker.bio ? (
                    <Text style={[styles.bio, { color: theme.textSecondary }]} numberOfLines={2}>{worker.bio}</Text>
                  ) : null}
                </View>
                <Ionicons name="chevron-forward" size={20} color={theme.textTertiary} />
              </TouchableOpacity>
              {worker.can_direct_hire !== false ? (
                <TouchableOpacity
                  style={[styles.bookButton, { borderColor: theme.primary }]}
                  onPress={() => handleBookDirectly(worker)}
                  accessibilityRole="button"
                >
                  <Ionicons name="flash-outline" size={16} color={theme.primary} />
                  <Text style={[styles.bookButtonText, { color: theme.primary }]}>{t('directHire.bookDirectly')}</Text>
                </TouchableOpacity>
              ) : (
                <Text style={[styles.notEligible, { color: theme.textSecondary }]}>{t('directHire.notEligible')}</Text>
              )}
              </View>
            ))
          )}

          <TouchableOpacity style={[styles.skipButton, { borderColor: theme.border }]} onPress={handleSkip}>
            <Text style={[styles.skipButtonText, { color: theme.textSecondary }]}>{t('jobsBoard.skipLetAdmin')}</Text>
          </TouchableOpacity>
        </ScrollView>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  loadingContainer: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  header: { padding: 20, paddingBottom: 8 },
  title: { fontSize: 22, fontFamily: 'Poppins_700Bold', marginBottom: 4 },
  subtitle: { fontSize: 13, fontFamily: 'Poppins_400Regular' },
  scrollContent: { padding: 20 },
  emptyState: { alignItems: 'center', paddingVertical: 60 },
  emptyTitle: { fontSize: 17, fontFamily: 'Poppins_600SemiBold', marginBottom: 6 },
  emptySubtitle: { fontSize: 14, fontFamily: 'Poppins_400Regular', textAlign: 'center', paddingHorizontal: 20 },
  cardWrap: { borderRadius: 14, borderWidth: 1, marginBottom: 12, padding: 14 },
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  bookButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    borderWidth: 1,
    borderRadius: 10,
    paddingVertical: 8,
    marginTop: 12,
  },
  bookButtonText: { fontSize: 13, fontFamily: 'Poppins_600SemiBold' },
  notEligible: { fontSize: 12, fontFamily: 'Poppins_400Regular', marginTop: 10, textAlign: 'center' },
  avatar: { width: 52, height: 52, borderRadius: 26 },
  avatarPlaceholder: { width: 52, height: 52, borderRadius: 26, justifyContent: 'center', alignItems: 'center' },
  avatarInitial: { color: '#FFFFFF', fontSize: 20, fontFamily: 'Poppins_700Bold' },
  cardBody: { flex: 1 },
  name: { fontSize: 15, fontFamily: 'Poppins_600SemiBold', marginBottom: 3 },
  metaRow: { flexDirection: 'row', alignItems: 'center', gap: 5, marginBottom: 2 },
  metaText: { fontSize: 12, fontFamily: 'Poppins_400Regular' },
  bio: { fontSize: 12, fontFamily: 'Poppins_400Regular', marginTop: 4 },
  skipButton: {
    borderWidth: 1,
    borderRadius: 10,
    paddingVertical: 12,
    alignItems: 'center',
    marginTop: 8,
  },
  skipButtonText: { fontSize: 14, fontFamily: 'Poppins_600SemiBold' },
});
