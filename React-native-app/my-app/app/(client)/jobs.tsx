import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
} from 'react-native';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../contexts/ThemeContext';
import Header from '../../components/Header';

interface Job {
  id: number;
  title: string;
  category: string;
  status: 'active' | 'in_progress' | 'completed' | 'cancelled';
  applicants?: number;
  workerName?: string;
  postedDate: string;
  budget?: number;
}

export default function ClientJobsScreen() {
  const { theme } = useTheme();
  const [activeTab, setActiveTab] = useState<'active' | 'completed'>('active');

  const [activeJobs] = useState<Job[]>([
    {
      id: 1,
      title: 'Fix Kitchen Sink Leak',
      category: 'Plumbing',
      status: 'active',
      applicants: 5,
      postedDate: '2 days ago',
      budget: 800,
    },
    {
      id: 2,
      title: 'Install Ceiling Fan',
      category: 'Electrical',
      status: 'in_progress',
      workerName: 'Ahmed Hassan',
      postedDate: '1 week ago',
      budget: 1200,
    },
    {
      id: 3,
      title: 'Paint Living Room',
      category: 'Painting',
      status: 'active',
      applicants: 8,
      postedDate: '3 days ago',
      budget: 4500,
    },
  ]);

  const [completedJobs] = useState<Job[]>([
    {
      id: 4,
      title: 'Repair Bathroom Tiles',
      category: 'Construction',
      status: 'completed',
      workerName: 'Mohammed Ali',
      postedDate: '2 weeks ago',
      budget: 2500,
    },
    {
      id: 5,
      title: 'Clean House',
      category: 'Cleaning',
      status: 'completed',
      workerName: 'Omar Abdullah',
      postedDate: '1 month ago',
      budget: 600,
    },
  ]);

  const getStatusBadgeStyle = (status: string) => {
    switch (status) {
      case 'active':
        return { backgroundColor: '#DBEAFE', color: '#1E40AF' };
      case 'in_progress':
        return { backgroundColor: '#FEF3C7', color: '#92400E' };
      case 'completed':
        return { backgroundColor: '#D1FAE5', color: '#065F46' };
      default:
        return { backgroundColor: '#F3F4F6', color: '#6B7280' };
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'active':
        return 'Open';
      case 'in_progress':
        return 'In Progress';
      case 'completed':
        return 'Completed';
      default:
        return status;
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active':
        return 'megaphone-outline';
      case 'in_progress':
        return 'settings-outline';
      case 'completed':
        return 'checkmark-circle';
      default:
        return 'help-circle';
    }
  };

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      <Header title="My Jobs" showBack={false} />

      {/* Post Job Button */}
      <View style={[styles.postJobSection, { backgroundColor: theme.card, borderBottomColor: theme.border }]}>
        <TouchableOpacity
          style={[styles.postJobButton, { backgroundColor: theme.primary }]}
          onPress={() => router.push('/(client)/post-job' as any)}
        >
          <Ionicons name="add" size={20} color={theme.textLight} />
          <Text style={[styles.postJobButtonText, { color: theme.textLight, fontFamily: 'Poppins_600SemiBold' }]}>Post New Job</Text>
        </TouchableOpacity>
      </View>

      {/* Tabs */}
      <View style={[styles.tabs, { backgroundColor: theme.card, borderBottomColor: theme.border }]}>
        <TouchableOpacity
          style={[
            styles.tab,
            activeTab === 'active' && { borderBottomColor: theme.primary },
          ]}
          onPress={() => setActiveTab('active')}
        >
          <Text
            style={[
              styles.tabText,
              { color: theme.textSecondary, fontFamily: 'Poppins_600SemiBold' },
              activeTab === 'active' && { color: theme.primary },
            ]}
          >
            Active & In Progress
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[
            styles.tab,
            activeTab === 'completed' && { borderBottomColor: theme.primary },
          ]}
          onPress={() => setActiveTab('completed')}
        >
          <Text
            style={[
              styles.tabText,
              { color: theme.textSecondary, fontFamily: 'Poppins_600SemiBold' },
              activeTab === 'completed' && { color: theme.primary },
            ]}
          >
            Completed
          </Text>
        </TouchableOpacity>
      </View>

      <ScrollView contentContainerStyle={styles.scrollContent}>
        {activeTab === 'active' ? (
          activeJobs.map((job) => (
            <TouchableOpacity
              key={job.id}
              style={[styles.jobCard, { backgroundColor: theme.card }]}
              onPress={() => router.push(`/(client)/job/${job.id}` as any)}
            >
              <View style={styles.jobHeader}>
                <Text style={[styles.jobTitle, { color: theme.text, fontFamily: 'Poppins_600SemiBold' }]}>{job.title}</Text>
                <View
                  style={[
                    styles.statusBadge,
                    { backgroundColor: getStatusBadgeStyle(job.status).backgroundColor },
                  ]}
                >
                  <Ionicons
                    name={getStatusIcon(job.status) as any}
                    size={12}
                    color={getStatusBadgeStyle(job.status).color}
                  />
                  <Text
                    style={[
                      styles.statusText,
                      { color: getStatusBadgeStyle(job.status).color, fontFamily: 'Poppins_600SemiBold' },
                    ]}
                  >
                    {getStatusText(job.status)}
                  </Text>
                </View>
              </View>

              <Text style={[styles.jobCategory, { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' }]}>{job.category}</Text>

              {job.status === 'active' && job.applicants && (
                <View style={[styles.applicantsRow, { backgroundColor: theme.background }]}>
                  <Ionicons name="people" size={14} color={theme.text} />
                  <Text style={[styles.applicantsText, { color: theme.text, fontFamily: 'Poppins_500Medium' }]}>
                    {' '}{job.applicants} applicant{job.applicants !== 1 ? 's' : ''}
                  </Text>
                </View>
              )}

              {job.status === 'in_progress' && job.workerName && (
                <View style={styles.workerRow}>
                  <Ionicons name="person" size={14} color="#065F46" />
                  <Text style={[styles.workerText, { fontFamily: 'Poppins_500Medium' }]}> Worker: {job.workerName}</Text>
                </View>
              )}

              <View style={[styles.jobFooter, { borderTopColor: theme.border }]}>
                <Text style={[styles.budgetText, { color: theme.primary, fontFamily: 'Poppins_600SemiBold' }]}>Budget: SDG {job.budget?.toLocaleString()}</Text>
                <Text style={[styles.dateText, { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' }]}>{job.postedDate}</Text>
              </View>
            </TouchableOpacity>
          ))
        ) : (
          completedJobs.map((job) => (
            <TouchableOpacity
              key={job.id}
              style={[styles.jobCard, { backgroundColor: theme.card }]}
              onPress={() => router.push(`/(client)/job/${job.id}` as any)}
            >
              <View style={styles.jobHeader}>
                <Text style={[styles.jobTitle, { color: theme.text, fontFamily: 'Poppins_600SemiBold' }]}>{job.title}</Text>
                <View
                  style={[
                    styles.statusBadge,
                    { backgroundColor: getStatusBadgeStyle(job.status).backgroundColor },
                  ]}
                >
                  <Ionicons
                    name={getStatusIcon(job.status) as any}
                    size={12}
                    color={getStatusBadgeStyle(job.status).color}
                  />
                  <Text
                    style={[
                      styles.statusText,
                      { color: getStatusBadgeStyle(job.status).color, fontFamily: 'Poppins_600SemiBold' },
                    ]}
                  >
                    {getStatusText(job.status)}
                  </Text>
                </View>
              </View>

              <Text style={[styles.jobCategory, { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' }]}>{job.category}</Text>

              {job.workerName && (
                <View style={styles.workerRow}>
                  <Ionicons name="person" size={14} color="#065F46" />
                  <Text style={[styles.workerText, { fontFamily: 'Poppins_500Medium' }]}> Worker: {job.workerName}</Text>
                </View>
              )}

              <View style={[styles.jobFooter, { borderTopColor: theme.border }]}>
                <Text style={[styles.budgetText, { color: theme.primary, fontFamily: 'Poppins_600SemiBold' }]}>Paid: SDG {job.budget?.toLocaleString()}</Text>
                <Text style={[styles.dateText, { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' }]}>Completed {job.postedDate}</Text>
              </View>
            </TouchableOpacity>
          ))
        )}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  postJobSection: {
    padding: 16,
    borderBottomWidth: 1,
  },
  postJobButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    paddingVertical: 12,
    borderRadius: 12,
  },
  postJobButtonText: {
    fontSize: 16,
  },
  tabs: {
    flexDirection: 'row',
    borderBottomWidth: 1,
  },
  tab: {
    flex: 1,
    paddingVertical: 16,
    alignItems: 'center',
    borderBottomWidth: 2,
    borderBottomColor: 'transparent',
  },
  tabText: {
    fontSize: 14,
  },
  scrollContent: {
    padding: 20,
  },
  jobCard: {
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  jobHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 8,
  },
  jobTitle: {
    flex: 1,
    fontSize: 16,
    marginRight: 8,
  },
  statusBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 6,
  },
  statusText: {
    fontSize: 11,
  },
  jobCategory: {
    fontSize: 13,
    marginBottom: 12,
  },
  applicantsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 10,
    borderRadius: 8,
    marginBottom: 12,
  },
  applicantsText: {
    fontSize: 14,
  },
  workerRow: {
    backgroundColor: '#ECFDF5',
    flexDirection: 'row',
    alignItems: 'center',
    padding: 10,
    borderRadius: 8,
    marginBottom: 12,
  },
  workerText: {
    fontSize: 14,
    color: '#065F46',
  },
  jobFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingTop: 12,
    borderTopWidth: 1,
  },
  budgetText: {
    fontSize: 14,
  },
  dateText: {
    fontSize: 12,
  },
});
