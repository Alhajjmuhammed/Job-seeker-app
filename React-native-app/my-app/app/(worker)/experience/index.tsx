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
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../../contexts/ThemeContext';
import Header from '../../../components/Header';
import apiService from '../../../services/api';

interface WorkExperience {
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

export default function ExperienceListScreen() {
  const { theme, isDark } = useTheme();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [experiences, setExperiences] = useState<WorkExperience[]>([]);

  useEffect(() => {
    loadExperiences();
  }, []);

  const loadExperiences = async () => {
    try {
      setLoading(true);
      const data = await apiService.getWorkExperiences();
      setExperiences(data);
    } catch (error) {
      console.error('Failed to load experiences:', error);
      Alert.alert('Error', 'Failed to load work experiences');
    } finally {
      setLoading(false);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await loadExperiences();
    setRefreshing(false);
  };

  const handleDelete = (experienceId: number, title: string) => {
    Alert.alert(
      'Delete Experience',
      `Are you sure you want to delete "${title}"?`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            try {
              await apiService.deleteWorkExperience(experienceId);
              Alert.alert('Success', 'Experience deleted successfully');
              loadExperiences();
            } catch (error) {
              console.error('Failed to delete experience:', error);
              Alert.alert('Error', 'Failed to delete experience');
            }
          },
        },
      ]
    );
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
  };

  const renderExperienceCard = (experience: WorkExperience) => (
    <View
      key={experience.id}
      style={[styles.experienceCard, { backgroundColor: theme.surface, shadowColor: isDark ? '#000' : '#000', shadowOpacity: isDark ? 0.3 : 0.1 }]}
    >
      {experience.is_current && (
        <View style={[styles.currentBadge, { backgroundColor: theme.primary }]}>
          <Text style={styles.currentBadgeText}>Current</Text>
        </View>
      )}

      <Text style={[styles.jobTitle, { color: theme.text }]}>{experience.job_title}</Text>
      <Text style={[styles.company, { color: theme.primary }]}>{experience.company}</Text>

      <View style={styles.metaContainer}>
        <View style={styles.metaItem}>
          <Ionicons name="calendar-outline" size={16} color={theme.textSecondary} />
          <Text style={[styles.metaText, { color: theme.textSecondary }]}>
            {formatDate(experience.start_date)} - {experience.is_current ? 'Present' : formatDate(experience.end_date!)}
          </Text>
        </View>

        {experience.location && (
          <View style={styles.metaItem}>
            <Ionicons name="location-outline" size={16} color={theme.textSecondary} />
            <Text style={[styles.metaText, { color: theme.textSecondary }]}>{experience.location}</Text>
          </View>
        )}

        {experience.duration && (
          <View style={styles.metaItem}>
            <Ionicons name="time-outline" size={16} color={theme.textSecondary} />
            <Text style={[styles.metaText, { color: theme.textSecondary }]}>{experience.duration}</Text>
          </View>
        )}
      </View>

      {experience.description && (
        <Text style={[styles.description, { color: theme.textSecondary }]} numberOfLines={3}>
          {experience.description}
        </Text>
      )}

      <View style={styles.actions}>
        <TouchableOpacity
          style={[styles.editButton, { borderColor: theme.primary }]}
          onPress={() => router.push(`/experience/${experience.id}/edit` as any)}
        >
          <Ionicons name="pencil" size={18} color={theme.primary} />
          <Text style={[styles.editButtonText, { color: theme.primary }]}>Edit</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.deleteButton}
          onPress={() => handleDelete(experience.id, experience.job_title)}
        >
          <Ionicons name="trash-outline" size={18} color="#EF4444" />
          <Text style={styles.deleteButtonText}>Delete</Text>
        </TouchableOpacity>
      </View>
    </View>
  );

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      <StatusBar style={theme.statusBar} />
      
      <Header showBack />

      {loading ? (
        <View style={[styles.loadingContainer, { backgroundColor: theme.background }]}>
          <ActivityIndicator size="large" color={theme.primary} />
          <Text style={[styles.loadingText, { color: theme.textSecondary }]}>Loading experiences...</Text>
        </View>
      ) : (
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
          <View style={styles.header}>
            <View style={styles.headerText}>
              <Text style={[styles.title, { color: theme.text }]}>My Experience</Text>
              <Text style={[styles.subtitle, { color: theme.textSecondary }]}>
                Showcase your professional work history
              </Text>
            </View>
            <TouchableOpacity
              style={[styles.addButton, { backgroundColor: theme.primary }]}
              onPress={() => router.push('/experience/add' as any)}
            >
              <Ionicons name="add" size={24} color="#FFFFFF" />
            </TouchableOpacity>
          </View>

          {experiences.length === 0 ? (
            <View style={styles.emptyState}>
              <Ionicons name="briefcase-outline" size={56} color={theme.textSecondary} style={{ marginBottom: 16 }} />
              <Text style={[styles.emptyTitle, { color: theme.text }]}>No Experience Added Yet</Text>
              <Text style={[styles.emptySubtitle, { color: theme.textSecondary }]}>
                Start building your professional profile by adding your work experience
              </Text>
              <TouchableOpacity
                style={[styles.addFirstButton, { backgroundColor: theme.primary }]}
                onPress={() => router.push('/experience/add' as any)}
              >
                <Ionicons name="add-circle-outline" size={20} color="#FFFFFF" />
                <Text style={styles.addFirstButtonText}>Add Your First Experience</Text>
              </TouchableOpacity>
            </View>
          ) : (
            <View style={styles.timeline}>
              {experiences.map(renderExperienceCard)}
            </View>
          )}
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
  },
  loadingText: {
    marginTop: 12,
    fontSize: 16,
    fontFamily: 'Poppins_400Regular',
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    padding: 20,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 24,
  },
  headerText: {
    flex: 1,
  },
  title: {
    fontSize: 28,
    fontFamily: 'Poppins_700Bold',
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 14,
    fontFamily: 'Poppins_400Regular',
  },
  addButton: {
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
  emptyState: {
    alignItems: 'center',
    paddingVertical: 60,
  },
  emptyTitle: {
    fontSize: 18,
    fontFamily: 'Poppins_600SemiBold',
    marginBottom: 6,
  },
  emptySubtitle: {
    fontSize: 15,
    fontFamily: 'Poppins_400Regular',
    textAlign: 'center',
    marginBottom: 24,
    paddingHorizontal: 20,
  },
  addFirstButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 12,
  },
  addFirstButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontFamily: 'Poppins_600SemiBold',
  },
  timeline: {
    gap: 16,
  },
  experienceCard: {
    padding: 20,
    borderRadius: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 3,
    position: 'relative',
  },
  currentBadge: {
    position: 'absolute',
    top: 12,
    right: 12,
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 12,
  },
  currentBadgeText: {
    color: '#FFFFFF',
    fontSize: 12,
    fontFamily: 'Poppins_600SemiBold',
  },
  jobTitle: {
    fontSize: 20,
    fontFamily: 'Poppins_700Bold',
    marginBottom: 4,
  },
  company: {
    fontSize: 16,
    fontFamily: 'Poppins_600SemiBold',
    marginBottom: 12,
  },
  metaContainer: {
    gap: 8,
    marginBottom: 12,
  },
  metaItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  metaText: {
    fontSize: 14,
    fontFamily: 'Poppins_400Regular',
  },
  description: {
    fontSize: 14,
    fontFamily: 'Poppins_400Regular',
    lineHeight: 20,
    marginBottom: 16,
  },
  actions: {
    flexDirection: 'row',
    gap: 12,
    paddingTop: 16,
    borderTopWidth: 1,
    borderTopColor: 'rgba(0,0,0,0.1)',
  },
  editButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    paddingVertical: 10,
    borderRadius: 10,
    borderWidth: 2,
  },
  editButtonText: {
    fontSize: 14,
    fontFamily: 'Poppins_600SemiBold',
  },
  deleteButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    paddingVertical: 10,
    borderRadius: 10,
    borderWidth: 2,
    borderColor: '#EF4444',
  },
  deleteButtonText: {
    fontSize: 14,
    fontFamily: 'Poppins_600SemiBold',
    color: '#EF4444',
  },
});
