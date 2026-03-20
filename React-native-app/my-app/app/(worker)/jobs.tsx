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
import { router } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../../contexts/AuthContext';
import { useTheme } from '../../contexts/ThemeContext';
import Header from '../../components/Header';
import apiService from '../../services/api';
import { useTranslation } from 'react-i18next';

interface AssignedJob {
  id: number;
  title: string;
  description?: string;
  total_price?: number;
  client_name: string;
  category_name?: string;
  status: 'pending' | 'assigned' | 'in_progress' | 'completed' | 'cancelled';
  created_at: string;
  preferred_date?: string;
  city?: string;
  location?: string;
}

export default function WorkerJobsScreen() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const { theme, isDark } = useTheme();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [assignedJobs, setAssignedJobs] = useState<AssignedJob[]>([]);
  const [selectedTab, setSelectedTab] = useState<'all' | 'pending' | 'active' | 'completed'>('all');

  useEffect(() => {
    let mounted = true;
    
    const loadData = async () => {
      try {
        setLoading(true);
        const response = await apiService.getWorkerAssignments();
        
        if (mounted) {
          setAssignedJobs(response.results || []);
        }
      } catch (error) {
        console.error('Error loading assigned jobs:', error);
        if (mounted) {
          Alert.alert(t('common.error'), t('jobs.failedLoadJobs'));
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    };

    loadData();

    return () => {
      mounted = false;
    };
  }, []);

  const onRefresh = async () => {
    setRefreshing(true);
    try {
      const response = await apiService.getWorkerAssignments();
      setAssignedJobs(response.results || []);
    } catch (error) {
      console.error('Error refreshing assigned jobs:', error);
      Alert.alert(t('common.error'), t('jobs.failedRefreshJobs'));
    } finally {
      setRefreshing(false);
    }
  };

  const navigateToJob = (job: AssignedJob) => {
    if (job.status === 'in_progress') {
      router.push('/(worker)/active-service' as any);
    } else {
      router.push(`/(worker)/service-assignment/${job.id}` as any);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'assigned': return '#FFA500';
      case 'in_progress': return '#2196F3';
      case 'completed': return '#4CAF50';
      case 'cancelled': return '#FF6B6B';
      default: return theme.textSecondary;
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'assigned': return 'NEW';
      case 'in_progress': return 'ACTIVE';
      case 'completed': return 'DONE';
      case 'cancelled': return 'CANCELLED';
      default: return status.toUpperCase();
    }
  };

  const filteredJobs = assignedJobs.filter(job => {
    switch (selectedTab) {
      case 'pending': return job.status === 'assigned';
      case 'active': return job.status === 'in_progress';
      case 'completed': return job.status === 'completed';
      case 'all':
      default: return true;
    }
  });

  const styles = StyleSheet.create({
    container: {
      flex: 1,
      backgroundColor: theme.background,
    },
    content: {
      flex: 1,
    },
    tabsContainer: {
      flexDirection: 'row',
      paddingHorizontal: 16,
      paddingVertical: 12,
      backgroundColor: theme.surface,
      borderBottomWidth: 1,
      borderBottomColor: theme.border,
    },
    tab: {
      flex: 1,
      paddingVertical: 12,
      alignItems: 'center',
      borderRadius: 8,
      marginHorizontal: 4,
    },
    activeTab: {
      backgroundColor: theme.primary,
    },
    tabText: {
      fontSize: 14,
      fontFamily: theme.fontSemiBold,
      color: theme.textSecondary,
    },
    activeTabText: {
      color: '#FFFFFF',
    },
    scrollContent: {
      padding: 16,
    },
    jobCard: {
      backgroundColor: theme.surface,
      borderRadius: 16,
      padding: 16,
      marginBottom: 16,
      shadowColor: '#000',
      shadowOffset: { width: 0, height: 2 },
      shadowOpacity: isDark ? 0.3 : 0.1,
      shadowRadius: 8,
      elevation: 3,
    },
    jobHeader: {
      flexDirection: 'row',
      justifyContent: 'space-between',
      alignItems: 'flex-start',
      marginBottom: 12,
    },
    statusBadge: {
      paddingHorizontal: 8,
      paddingVertical: 4,
      borderRadius: 12,
      minWidth: 50,
      alignItems: 'center',
    },
    statusText: {
      fontSize: 10,
      fontFamily: theme.fontBold,
      color: '#FFFFFF',
    },
    jobTitle: {
      fontSize: 18,
      fontFamily: theme.fontSemiBold,
      color: theme.text,
      marginBottom: 8,
      flex: 1,
      marginRight: 12,
    },
    jobDescription: {
      fontSize: 14,
      fontFamily: theme.fontRegular,
      color: theme.textSecondary,
      marginBottom: 16,
    },
    jobDetails: {
      marginBottom: 16,
    },
    detailRow: {
      flexDirection: 'row',
      justifyContent: 'space-between',
      marginBottom: 8,
    },
    detailLabel: {
      fontSize: 14,
      fontFamily: theme.fontRegular,
      color: theme.textSecondary,
    },
    detailValue: {
      fontSize: 14,
      fontFamily: theme.fontSemiBold,
      color: theme.text,
    },
    clientInfo: {
      backgroundColor: isDark ? theme.primaryDark : '#F8FAFC',
      borderRadius: 8,
      padding: 12,
      marginBottom: 16,
    },
    clientName: {
      fontSize: 16,
      fontFamily: theme.fontSemiBold,
      color: theme.text,
      marginBottom: 4,
    },
    clientEmail: {
      fontSize: 14,
      fontFamily: theme.fontRegular,
      color: theme.textSecondary,
    },
    jobActions: {
      flexDirection: 'row',
      gap: 12,
    },
    actionButton: {
      flex: 1,
      height: 44,
      borderRadius: 10,
      justifyContent: 'center',
      alignItems: 'center',
      flexDirection: 'row',
      gap: 8,
    },
    startButton: {
      backgroundColor: theme.primary,
    },
    completeButton: {
      backgroundColor: '#4CAF50',
    },
    disabledButton: {
      backgroundColor: theme.textTertiary,
    },
    actionButtonText: {
      fontSize: 14,
      fontFamily: theme.fontSemiBold,
      color: '#FFFFFF',
    },
    emptyState: {
      flex: 1,
      justifyContent: 'center',
      alignItems: 'center',
      paddingHorizontal: 32,
    },
    emptyIcon: {
      marginBottom: 16,
    },
    emptyTitle: {
      fontSize: 18,
      fontFamily: theme.fontSemiBold,
      color: theme.text,
      textAlign: 'center',
      marginBottom: 8,
    },
    emptySubtitle: {
      fontSize: 14,
      fontFamily: theme.fontRegular,
      color: theme.textSecondary,
      textAlign: 'center',
      lineHeight: 20,
    },
    loadingContainer: {
      flex: 1,
      justifyContent: 'center',
      alignItems: 'center',
    },
    loadingText: {
      marginTop: 12,
      fontSize: 16,
      fontFamily: theme.fontRegular,
      color: theme.textSecondary,
    },
  });

  if (loading) {
    return (
      <View style={styles.container}>
        <Header title="My Jobs" showBack />
        <StatusBar style={isDark ? 'light' : 'dark'} />
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={theme.primary} />
          <Text style={styles.loadingText}>{t('jobs.loadingJobs')}</Text>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Header title="My Jobs" showBack />
      <StatusBar style={isDark ? 'light' : 'dark'} />
      
      {/* Tabs */}
      <View style={styles.tabsContainer}>
        <TouchableOpacity
          style={[styles.tab, selectedTab === 'all' && styles.activeTab]}
          onPress={() => setSelectedTab('all')}
        >
          <Text style={[styles.tabText, selectedTab === 'all' && styles.activeTabText]}>
            All ({assignedJobs.length})
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.tab, selectedTab === 'pending' && styles.activeTab]}
          onPress={() => setSelectedTab('pending')}
        >
          <Text style={[styles.tabText, selectedTab === 'pending' && styles.activeTabText]}>
            Pending ({assignedJobs.filter(j => j.status === 'assigned').length})
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.tab, selectedTab === 'active' && styles.activeTab]}
          onPress={() => setSelectedTab('active')}
        >
          <Text style={[styles.tabText, selectedTab === 'active' && styles.activeTabText]}>
            Active ({assignedJobs.filter(j => j.status === 'in_progress').length})
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.tab, selectedTab === 'completed' && styles.activeTab]}
          onPress={() => setSelectedTab('completed')}
        >
          <Text style={[styles.tabText, selectedTab === 'completed' && styles.activeTabText]}>
            Done ({assignedJobs.filter(j => j.status === 'completed').length})
          </Text>
        </TouchableOpacity>
      </View>

      <ScrollView
        style={styles.content}
        contentContainerStyle={styles.scrollContent}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
      >
        {filteredJobs.length === 0 ? (
          <View style={styles.emptyState}>
            <Ionicons
              name="briefcase-outline"
              size={64}
              color={theme.textSecondary}
              style={styles.emptyIcon}
            />
            <Text style={styles.emptyTitle}>
              {selectedTab === 'all' 
                ? 'No jobs assigned yet' 
                : `No ${selectedTab} jobs`}
            </Text>
            <Text style={styles.emptySubtitle}>
              {selectedTab === 'all'
                ? 'Jobs assigned to you will appear here'
                : `Your ${selectedTab} jobs will appear here`}
            </Text>
          </View>
        ) : (
          filteredJobs.map((job) => (
            <View key={job.id} style={styles.jobCard}>
              <View style={styles.jobHeader}>
                <Text style={styles.jobTitle}>{job.title}</Text>
                <View style={[styles.statusBadge, { backgroundColor: getStatusColor(job.status) }]}>
                  <Text style={styles.statusText}>{getStatusText(job.status)}</Text>
                </View>
              </View>

              {job.description && (
                <Text style={styles.jobDescription}>{job.description}</Text>
              )}

              <View style={styles.clientInfo}>
                <Text style={styles.clientName}>{job.client_name}</Text>
                {job.category_name && (
                  <Text style={styles.clientEmail}>{job.category_name}</Text>
                )}
              </View>

              <View style={styles.jobDetails}>
                {job.total_price && (
                  <View style={styles.detailRow}>
                    <Text style={styles.detailLabel}>Price:</Text>
                    <Text style={styles.detailValue}>
                      TSH {job.total_price}
                    </Text>
                  </View>
                )}
                <View style={styles.detailRow}>
                  <Text style={styles.detailLabel}>Posted:</Text>
                  <Text style={styles.detailValue}>
                    {new Date(job.created_at).toLocaleDateString()}
                  </Text>
                </View>
                {job.preferred_date && (
                  <View style={styles.detailRow}>
                    <Text style={styles.detailLabel}>Preferred Date:</Text>
                    <Text style={styles.detailValue}>
                      {new Date(job.preferred_date).toLocaleDateString()}
                    </Text>
                  </View>
                )}
                {(job.city || job.location) && (
                  <View style={styles.detailRow}>
                    <Text style={styles.detailLabel}>Location:</Text>
                    <Text style={styles.detailValue}>{job.city || job.location}</Text>
                  </View>
                )}
              </View>

              {/* Action button */}
              <View style={styles.jobActions}>
                {job.status !== 'completed' && job.status !== 'cancelled' && (
                  <TouchableOpacity
                    style={[styles.actionButton, job.status === 'in_progress' ? styles.completeButton : styles.startButton]}
                    onPress={() => navigateToJob(job)}
                  >
                    <Ionicons name={job.status === 'in_progress' ? 'time' : 'arrow-forward'} size={16} color="#FFFFFF" />
                    <Text style={styles.actionButtonText}>
                      {job.status === 'in_progress' ? 'Active Session' : 'View Assignment'}
                    </Text>
                  </TouchableOpacity>
                )}
                {job.status === 'completed' && (
                  <View style={[styles.actionButton, styles.disabledButton]}>
                    <Ionicons name="checkmark-circle" size={16} color="#FFFFFF" />
                    <Text style={styles.actionButtonText}>{t('assignments.completed')}</Text>
                  </View>
                )}
              </View>
            </View>
          ))
        )}
      </ScrollView>
    </View>
  );
}
