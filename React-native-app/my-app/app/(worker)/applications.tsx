import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  RefreshControl,
  Alert,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../contexts/ThemeContext';
import Header from '../../components/Header';
import apiService from '../../services/api';

interface Application {
  id: number;
  job_id: number;
  job_title: string;
  client_name: string;
  applied_date: string;
  status: string;
  cover_letter?: string;
  offered_rate?: string;
  job_description?: string;
}

type FilterType = 'all' | 'pending' | 'accepted' | 'rejected';

export default function ApplicationsScreen() {
  const { theme, isDark } = useTheme();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [applications, setApplications] = useState<Application[]>([]);
  const [filter, setFilter] = useState<FilterType>('all');

  useEffect(() => {
    loadApplications();
  }, []);

  const loadApplications = async () => {
    try {
      setLoading(true);
      const data = await apiService.getWorkerApplications();
      setApplications(data || []);
    } catch (error) {
      console.error('Error loading applications:', error);
      Alert.alert('Error', 'Failed to load applications');
    } finally {
      setLoading(false);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await loadApplications();
    setRefreshing(false);
  };

  const handleWithdrawApplication = (applicationId: number) => {
    Alert.alert(
      'Withdraw Application',
      'Are you sure you want to withdraw this application?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Withdraw',
          style: 'destructive',
          onPress: () => withdrawApplication(applicationId),
        },
      ]
    );
  };

  const withdrawApplication = async (applicationId: number) => {
    try {
      // TODO: Implement withdraw API endpoint
      Alert.alert('Coming Soon', 'Withdraw functionality will be available soon');
      // await apiService.withdrawApplication(applicationId);
      // await loadApplications();
    } catch (error) {
      console.error('Error withdrawing application:', error);
      Alert.alert('Error', 'Failed to withdraw application');
    }
  };

  const getFilteredApplications = () => {
    if (filter === 'all') return applications;
    return applications.filter((app) => app.status === filter);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'accepted':
        return '#10B981';
      case 'rejected':
        return '#EF4444';
      case 'pending':
        return '#F59E0B';
      default:
        return theme.textSecondary;
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'accepted':
        return 'checkmark-circle';
      case 'rejected':
        return 'close-circle';
      case 'pending':
        return 'time';
      default:
        return 'help-circle';
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffTime = Math.abs(now.getTime() - date.getTime());
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;
    if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
    return date.toLocaleDateString();
  };

  const filteredApplications = getFilteredApplications();
  const stats = {
    all: applications.length,
    pending: applications.filter((a) => a.status === 'pending').length,
    accepted: applications.filter((a) => a.status === 'accepted').length,
    rejected: applications.filter((a) => a.status === 'rejected').length,
  };

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      <StatusBar style={theme.statusBar} />
      <Header showBack title="My Applications" />

      {/* Filter Tabs */}
      <View style={[styles.filterContainer, { backgroundColor: theme.surface }]}>
        <ScrollView horizontal showsHorizontalScrollIndicator={false}>
          <TouchableOpacity
            style={[
              styles.filterTab,
              filter === 'all' && { backgroundColor: theme.primary },
            ]}
            onPress={() => setFilter('all')}
          >
            <Text
              style={[
                styles.filterTabText,
                { color: filter === 'all' ? '#FFFFFF' : theme.text },
              ]}
            >
              All ({stats.all})
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[
              styles.filterTab,
              filter === 'pending' && { backgroundColor: '#F59E0B' },
            ]}
            onPress={() => setFilter('pending')}
          >
            <Text
              style={[
                styles.filterTabText,
                { color: filter === 'pending' ? '#FFFFFF' : theme.text },
              ]}
            >
              Pending ({stats.pending})
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[
              styles.filterTab,
              filter === 'accepted' && { backgroundColor: '#10B981' },
            ]}
            onPress={() => setFilter('accepted')}
          >
            <Text
              style={[
                styles.filterTabText,
                { color: filter === 'accepted' ? '#FFFFFF' : theme.text },
              ]}
            >
              Accepted ({stats.accepted})
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[
              styles.filterTab,
              filter === 'rejected' && { backgroundColor: '#EF4444' },
            ]}
            onPress={() => setFilter('rejected')}
          >
            <Text
              style={[
                styles.filterTabText,
                { color: filter === 'rejected' ? '#FFFFFF' : theme.text },
              ]}
            >
              Rejected ({stats.rejected})
            </Text>
          </TouchableOpacity>
        </ScrollView>
      </View>

      {loading ? (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={theme.primary} />
          <Text style={[styles.loadingText, { color: theme.textSecondary }]}>
            Loading applications...
          </Text>
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
          {filteredApplications.length === 0 ? (
            <View style={[styles.emptyState, { backgroundColor: theme.surface }]}>
              <Ionicons name="document-text-outline" size={64} color={theme.textSecondary} />
              <Text style={[styles.emptyText, { color: theme.text }]}>
                {filter === 'all' ? 'No applications yet' : `No ${filter} applications`}
              </Text>
              <Text style={[styles.emptySubtext, { color: theme.textSecondary }]}>
                {filter === 'all'
                  ? 'Browse jobs and start applying'
                  : 'Try selecting a different filter'}
              </Text>
              {filter === 'all' && (
                <TouchableOpacity
                  style={[styles.browseButton, { backgroundColor: theme.primary }]}
                  onPress={() => router.push('/browse-jobs' as any)}
                >
                  <Text style={styles.browseButtonText}>Browse Jobs</Text>
                </TouchableOpacity>
              )}
            </View>
          ) : (
            filteredApplications.map((application) => (
              <TouchableOpacity
                key={application.id}
                style={[styles.applicationCard, { backgroundColor: theme.surface }]}
                onPress={() => router.push(`/(worker)/job/${application.job_id}` as any)}
              >
                <View style={styles.cardHeader}>
                  <View style={styles.headerLeft}>
                    <Ionicons name="briefcase" size={24} color={theme.primary} />
                    <View style={styles.titleContainer}>
                      <Text style={[styles.jobTitle, { color: theme.text }]}>
                        {application.job_title}
                      </Text>
                      <Text style={[styles.clientName, { color: theme.textSecondary }]}>
                        {application.client_name}
                      </Text>
                    </View>
                  </View>
                  <View
                    style={[
                      styles.statusBadge,
                      { backgroundColor: getStatusColor(application.status) + '20' },
                    ]}
                  >
                    <Ionicons
                      name={getStatusIcon(application.status) as any}
                      size={16}
                      color={getStatusColor(application.status)}
                    />
                    <Text
                      style={[
                        styles.statusText,
                        { color: getStatusColor(application.status) },
                      ]}
                    >
                      {application.status.charAt(0).toUpperCase() + application.status.slice(1)}
                    </Text>
                  </View>
                </View>

                <View style={styles.cardContent}>
                  <View style={styles.infoRow}>
                    <Ionicons name="calendar-outline" size={16} color={theme.textSecondary} />
                    <Text style={[styles.infoText, { color: theme.textSecondary }]}>
                      Applied {formatDate(application.applied_date)}
                    </Text>
                  </View>

                  {application.offered_rate && (
                    <View style={styles.infoRow}>
                      <Ionicons name="cash-outline" size={16} color={theme.textSecondary} />
                      <Text style={[styles.infoText, { color: theme.textSecondary }]}>
                        Rate: ${application.offered_rate}/hr
                      </Text>
                    </View>
                  )}

                  {application.cover_letter && (
                    <View style={[styles.coverLetterContainer, { backgroundColor: theme.background }]}>
                      <Text style={[styles.coverLetterLabel, { color: theme.textSecondary }]}>
                        Cover Letter:
                      </Text>
                      <Text style={[styles.coverLetterText, { color: theme.text }]} numberOfLines={3}>
                        {application.cover_letter}
                      </Text>
                    </View>
                  )}
                </View>

                <View style={styles.cardFooter}>
                  <TouchableOpacity
                    style={[styles.viewButton, { borderColor: theme.border }]}
                    onPress={() => router.push(`/(worker)/job/${application.job_id}` as any)}
                  >
                    <Text style={[styles.viewButtonText, { color: theme.primary }]}>View Job</Text>
                    <Ionicons name="arrow-forward" size={16} color={theme.primary} />
                  </TouchableOpacity>

                  {application.status === 'pending' && (
                    <TouchableOpacity
                      style={[styles.withdrawButton, { backgroundColor: '#EF444420', borderColor: '#EF4444' }]}
                      onPress={() => handleWithdrawApplication(application.id)}
                    >
                      <Text style={[styles.withdrawButtonText, { color: '#EF4444' }]}>Withdraw</Text>
                    </TouchableOpacity>
                  )}
                </View>
              </TouchableOpacity>
            ))
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
    gap: 12,
  },
  loadingText: {
    fontSize: 15,
    fontFamily: 'Poppins_400Regular',
  },
  filterContainer: {
    paddingVertical: 12,
    paddingHorizontal: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  filterTab: {
    paddingHorizontal: 20,
    paddingVertical: 8,
    borderRadius: 20,
    marginRight: 12,
  },
  filterTabText: {
    fontSize: 14,
    fontFamily: 'Poppins_600SemiBold',
  },
  scrollContent: {
    padding: 16,
    paddingBottom: 40,
  },
  emptyState: {
    alignItems: 'center',
    justifyContent: 'center',
    padding: 40,
    borderRadius: 16,
    marginTop: 40,
  },
  emptyText: {
    fontSize: 20,
    fontFamily: 'Poppins_600SemiBold',
    marginTop: 16,
    marginBottom: 8,
  },
  emptySubtext: {
    fontSize: 14,
    fontFamily: 'Poppins_400Regular',
    textAlign: 'center',
    marginBottom: 24,
  },
  browseButton: {
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 12,
  },
  browseButtonText: {
    color: '#FFFFFF',
    fontSize: 15,
    fontFamily: 'Poppins_600SemiBold',
  },
  applicationCard: {
    borderRadius: 16,
    padding: 16,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 8,
    elevation: 3,
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  headerLeft: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    flex: 1,
    gap: 12,
  },
  titleContainer: {
    flex: 1,
  },
  jobTitle: {
    fontSize: 16,
    fontFamily: 'Poppins_600SemiBold',
    marginBottom: 4,
  },
  clientName: {
    fontSize: 13,
    fontFamily: 'Poppins_400Regular',
  },
  statusBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
  },
  statusText: {
    fontSize: 12,
    fontFamily: 'Poppins_600SemiBold',
  },
  cardContent: {
    gap: 8,
    marginBottom: 12,
  },
  infoRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  infoText: {
    fontSize: 13,
    fontFamily: 'Poppins_400Regular',
  },
  coverLetterContainer: {
    padding: 12,
    borderRadius: 8,
    marginTop: 8,
  },
  coverLetterLabel: {
    fontSize: 12,
    fontFamily: 'Poppins_600SemiBold',
    marginBottom: 4,
  },
  coverLetterText: {
    fontSize: 13,
    fontFamily: 'Poppins_400Regular',
    lineHeight: 20,
  },
  cardFooter: {
    flexDirection: 'row',
    gap: 12,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#E5E7EB',
  },
  viewButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    paddingVertical: 10,
    borderRadius: 8,
    borderWidth: 1,
  },
  viewButtonText: {
    fontSize: 14,
    fontFamily: 'Poppins_600SemiBold',
  },
  withdrawButton: {
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 8,
    borderWidth: 1,
  },
  withdrawButtonText: {
    fontSize: 14,
    fontFamily: 'Poppins_600SemiBold',
  },
});
