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
  Image,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import * as WebBrowser from 'expo-web-browser';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../contexts/ThemeContext';
import Header from '../../components/Header';
import apiService from '../../services/api';
import { useTranslation } from 'react-i18next';

interface CVExperience {
  id: number;
  job_title: string;
  company: string;
  location: string;
  start_date: string;
  end_date: string | null;
  is_current: boolean;
  description: string;
  duration?: string;
}

interface CVTag {
  id: number;
  name: string;
}

interface CVData {
  full_name: string;
  email: string;
  phone_number: string;
  location: string;
  bio: string;
  worker_type: string;
  experience_years: number;
  average_rating: string;
  completed_jobs: number;
  verification_status: string;
  profile_image_url: string | null;
  is_complete: boolean;
  categories: CVTag[];
  skills: CVTag[];
  experiences: CVExperience[];
}

export default function CVScreen() {
  const { t } = useTranslation();
  const { theme } = useTheme();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [cv, setCv] = useState<CVData | null>(null);

  useEffect(() => {
    loadCV();
  }, []);

  const loadCV = async () => {
    try {
      setLoading(true);
      const data = await apiService.getMyCV();
      setCv(data);
    } catch (error) {
      console.error('Failed to load CV:', error);
      Alert.alert(t('common.error'), 'Failed to load your CV');
    } finally {
      setLoading(false);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await loadCV();
    setRefreshing(false);
  };

  const handleDownload = async () => {
    try {
      setDownloading(true);
      const url = await apiService.getMyCVDownloadUrl();
      await WebBrowser.openBrowserAsync(url);
    } catch (error) {
      console.error('Failed to download CV:', error);
      Alert.alert(t('common.error'), 'Failed to download your CV');
    } finally {
      setDownloading(false);
    }
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'Present';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
  };

  if (loading) {
    return (
      <View style={[styles.container, { backgroundColor: theme.background }]}>
        <StatusBar style={theme.statusBar} />
        <Header showBack />
        <View style={[styles.loadingContainer, { backgroundColor: theme.background }]}>
          <ActivityIndicator size="large" color={theme.primary} />
          <Text style={[styles.loadingText, { color: theme.textSecondary }]}>Loading your CV...</Text>
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
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={theme.primary} colors={[theme.primary]} />
        }
      >
        <View style={styles.header}>
          <View style={styles.headerText}>
            <Text style={[styles.title, { color: theme.text }]}>My CV</Text>
            <Text style={[styles.subtitle, { color: theme.textSecondary }]}>Automatically generated from your profile</Text>
          </View>
          <TouchableOpacity
            style={[styles.downloadButton, { backgroundColor: theme.primary }]}
            onPress={handleDownload}
            disabled={downloading}
          >
            {downloading ? (
              <ActivityIndicator size="small" color="#FFFFFF" />
            ) : (
              <Ionicons name="download-outline" size={22} color="#FFFFFF" />
            )}
          </TouchableOpacity>
        </View>

        {cv && !cv.is_complete && (
          <View style={[styles.noticeBox, { backgroundColor: theme.surface, borderColor: theme.border }]}>
            <Ionicons name="alert-circle-outline" size={20} color={theme.primary} />
            <Text style={[styles.noticeText, { color: theme.textSecondary }]}>
              Your CV will look stronger with a complete profile - add a bio, skills and work experience.
            </Text>
          </View>
        )}

        {cv && (
          <View style={[styles.card, { backgroundColor: theme.surface, borderColor: theme.border }]}>
            <View style={styles.cardHeaderRow}>
              {cv.profile_image_url ? (
                <Image source={{ uri: cv.profile_image_url }} style={styles.avatar} />
              ) : (
                <View style={[styles.avatarPlaceholder, { backgroundColor: theme.primary }]}>
                  <Text style={styles.avatarInitial}>{cv.full_name?.charAt(0)?.toUpperCase() || 'W'}</Text>
                </View>
              )}
              <View style={styles.cardHeaderText}>
                <Text style={[styles.name, { color: theme.text }]}>{cv.full_name}</Text>
                <Text style={[styles.workerType, { color: theme.textSecondary }]}>{cv.worker_type}</Text>
                {cv.verification_status === 'verified' && (
                  <View style={[styles.verifiedBadge, { backgroundColor: theme.primary }]}>
                    <Text style={styles.verifiedBadgeText}>Verified Worker</Text>
                  </View>
                )}
              </View>
            </View>

            <View style={styles.statsRow}>
              <View style={styles.statBox}>
                <Text style={[styles.statValue, { color: theme.primary }]}>{cv.experience_years}</Text>
                <Text style={[styles.statLabel, { color: theme.textSecondary }]}>Years Exp.</Text>
              </View>
              <View style={styles.statBox}>
                <Text style={[styles.statValue, { color: theme.primary }]}>{cv.completed_jobs}</Text>
                <Text style={[styles.statLabel, { color: theme.textSecondary }]}>Jobs Done</Text>
              </View>
              <View style={styles.statBox}>
                <Text style={[styles.statValue, { color: theme.primary }]}>{cv.average_rating}</Text>
                <Text style={[styles.statLabel, { color: theme.textSecondary }]}>Rating</Text>
              </View>
            </View>

            {cv.bio ? (
              <View style={styles.section}>
                <Text style={[styles.sectionTitle, { color: theme.primary }]}>ABOUT</Text>
                <Text style={[styles.bodyText, { color: theme.text }]}>{cv.bio}</Text>
              </View>
            ) : null}

            {cv.categories.length > 0 && (
              <View style={styles.section}>
                <Text style={[styles.sectionTitle, { color: theme.primary }]}>SERVICE CATEGORIES</Text>
                <View style={styles.tagList}>
                  {cv.categories.map((c) => (
                    <View key={`cat-${c.id}`} style={[styles.tag, { borderColor: theme.primary }]}>
                      <Text style={[styles.tagText, { color: theme.primary }]}>{c.name}</Text>
                    </View>
                  ))}
                </View>
              </View>
            )}

            {cv.skills.length > 0 && (
              <View style={styles.section}>
                <Text style={[styles.sectionTitle, { color: theme.primary }]}>SKILLS</Text>
                <View style={styles.tagList}>
                  {cv.skills.map((s) => (
                    <View key={`skill-${s.id}`} style={[styles.tag, { borderColor: theme.primary }]}>
                      <Text style={[styles.tagText, { color: theme.primary }]}>{s.name}</Text>
                    </View>
                  ))}
                </View>
              </View>
            )}

            {cv.experiences.length > 0 && (
              <View style={styles.section}>
                <Text style={[styles.sectionTitle, { color: theme.primary }]}>WORK EXPERIENCE</Text>
                {cv.experiences.map((exp) => (
                  <View key={exp.id} style={[styles.experienceItem, { borderBottomColor: theme.divider }]}>
                    <Text style={[styles.jobTitle, { color: theme.text }]}>{exp.job_title}</Text>
                    <Text style={[styles.company, { color: theme.primary }]}>{exp.company}</Text>
                    <Text style={[styles.meta, { color: theme.textSecondary }]}>
                      {formatDate(exp.start_date)} - {exp.is_current ? 'Present' : formatDate(exp.end_date)}
                      {exp.duration ? ` · ${exp.duration}` : ''}
                    </Text>
                    {exp.description ? (
                      <Text style={[styles.description, { color: theme.textSecondary }]}>{exp.description}</Text>
                    ) : null}
                  </View>
                ))}
              </View>
            )}
          </View>
        )}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  loadingContainer: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  loadingText: { marginTop: 12, fontSize: 16, fontFamily: 'Poppins_400Regular' },
  scrollView: { flex: 1 },
  scrollContent: { padding: 20 },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 20,
  },
  headerText: { flex: 1 },
  title: { fontSize: 28, fontFamily: 'Poppins_700Bold', marginBottom: 4 },
  subtitle: { fontSize: 14, fontFamily: 'Poppins_400Regular' },
  downloadButton: {
    width: 48,
    height: 48,
    borderRadius: 24,
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 4,
    elevation: 4,
  },
  noticeBox: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 10,
    padding: 14,
    borderRadius: 12,
    borderWidth: 1,
    marginBottom: 16,
  },
  noticeText: { flex: 1, fontSize: 13, fontFamily: 'Poppins_400Regular', lineHeight: 18 },
  card: {
    borderRadius: 16,
    borderWidth: 1,
    padding: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 8,
    elevation: 2,
  },
  cardHeaderRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 16 },
  avatar: { width: 56, height: 56, borderRadius: 28, marginRight: 14 },
  avatarPlaceholder: {
    width: 56,
    height: 56,
    borderRadius: 28,
    marginRight: 14,
    justifyContent: 'center',
    alignItems: 'center',
  },
  avatarInitial: { color: '#FFFFFF', fontSize: 22, fontFamily: 'Poppins_700Bold' },
  cardHeaderText: { flex: 1 },
  name: { fontSize: 19, fontFamily: 'Poppins_700Bold' },
  workerType: { fontSize: 13, fontFamily: 'Poppins_400Regular', textTransform: 'uppercase', marginTop: 2 },
  verifiedBadge: { alignSelf: 'flex-start', borderRadius: 10, paddingHorizontal: 10, paddingVertical: 3, marginTop: 6 },
  verifiedBadgeText: { color: '#FFFFFF', fontSize: 11, fontFamily: 'Poppins_600SemiBold' },
  statsRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    paddingVertical: 14,
    borderTopWidth: 1,
    borderBottomWidth: 1,
    borderColor: 'rgba(0,0,0,0.08)',
    marginBottom: 16,
  },
  statBox: { alignItems: 'center' },
  statValue: { fontSize: 20, fontFamily: 'Poppins_700Bold' },
  statLabel: { fontSize: 11, fontFamily: 'Poppins_400Regular', textTransform: 'uppercase', marginTop: 2 },
  section: { marginBottom: 18 },
  sectionTitle: { fontSize: 12, fontFamily: 'Poppins_600SemiBold', letterSpacing: 0.5, marginBottom: 10 },
  bodyText: { fontSize: 14, fontFamily: 'Poppins_400Regular', lineHeight: 20 },
  tagList: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  tag: { borderWidth: 1, borderRadius: 14, paddingHorizontal: 12, paddingVertical: 5 },
  tagText: { fontSize: 13, fontFamily: 'Poppins_400Regular' },
  experienceItem: { paddingBottom: 14, marginBottom: 14, borderBottomWidth: 1 },
  jobTitle: { fontSize: 15, fontFamily: 'Poppins_600SemiBold' },
  company: { fontSize: 13, fontFamily: 'Poppins_400Regular', marginTop: 1 },
  meta: { fontSize: 12, fontFamily: 'Poppins_400Regular', marginTop: 4, marginBottom: 6 },
  description: { fontSize: 13, fontFamily: 'Poppins_400Regular', lineHeight: 18 },
});
