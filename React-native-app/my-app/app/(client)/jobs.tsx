import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { router } from 'expo-router';

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
        return '📢 Open';
      case 'in_progress':
        return '⚙️ In Progress';
      case 'completed':
        return '✓ Completed';
      default:
        return status;
    }
  };

  return (
    <View style={styles.container}>
      <StatusBar style="light" />
      
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>My Jobs</Text>
        <TouchableOpacity
          style={styles.postJobButton}
          onPress={() => router.push('/(client)/post-job')}
        >
          <Text style={styles.postJobButtonText}>+ Post Job</Text>
        </TouchableOpacity>
      </View>

      {/* Tabs */}
      <View style={styles.tabs}>
        <TouchableOpacity
          style={[styles.tab, activeTab === 'active' && styles.tabActive]}
          onPress={() => setActiveTab('active')}
        >
          <Text style={[styles.tabText, activeTab === 'active' && styles.tabTextActive]}>
            Active & In Progress
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.tab, activeTab === 'completed' && styles.tabActive]}
          onPress={() => setActiveTab('completed')}
        >
          <Text style={[styles.tabText, activeTab === 'completed' && styles.tabTextActive]}>
            Completed
          </Text>
        </TouchableOpacity>
      </View>

      <ScrollView contentContainerStyle={styles.scrollContent}>
        {activeTab === 'active' ? (
          activeJobs.map((job) => (
            <TouchableOpacity
              key={job.id}
              style={styles.jobCard}
              onPress={() => router.push(`/(client)/job/${job.id}`)}
            >
              <View style={styles.jobHeader}>
                <Text style={styles.jobTitle}>{job.title}</Text>
                <View
                  style={[
                    styles.statusBadge,
                    { backgroundColor: getStatusBadgeStyle(job.status).backgroundColor },
                  ]}
                >
                  <Text
                    style={[
                      styles.statusText,
                      { color: getStatusBadgeStyle(job.status).color },
                    ]}
                  >
                    {getStatusText(job.status)}
                  </Text>
                </View>
              </View>

              <Text style={styles.jobCategory}>{job.category}</Text>

              {job.status === 'active' && job.applicants && (
                <View style={styles.applicantsRow}>
                  <Text style={styles.applicantsText}>
                    👥 {job.applicants} applicant{job.applicants !== 1 ? 's' : ''}
                  </Text>
                </View>
              )}

              {job.status === 'in_progress' && job.workerName && (
                <View style={styles.workerRow}>
                  <Text style={styles.workerText}>👷 Worker: {job.workerName}</Text>
                </View>
              )}

              <View style={styles.jobFooter}>
                <Text style={styles.budgetText}>Budget: SDG {job.budget?.toLocaleString()}</Text>
                <Text style={styles.dateText}>{job.postedDate}</Text>
              </View>
            </TouchableOpacity>
          ))
        ) : (
          completedJobs.map((job) => (
            <TouchableOpacity
              key={job.id}
              style={styles.jobCard}
              onPress={() => router.push(`/(client)/job/${job.id}`)}
            >
              <View style={styles.jobHeader}>
                <Text style={styles.jobTitle}>{job.title}</Text>
                <View
                  style={[
                    styles.statusBadge,
                    { backgroundColor: getStatusBadgeStyle(job.status).backgroundColor },
                  ]}
                >
                  <Text
                    style={[
                      styles.statusText,
                      { color: getStatusBadgeStyle(job.status).color },
                    ]}
                  >
                    {getStatusText(job.status)}
                  </Text>
                </View>
              </View>

              <Text style={styles.jobCategory}>{job.category}</Text>

              {job.workerName && (
                <View style={styles.workerRow}>
                  <Text style={styles.workerText}>👷 Worker: {job.workerName}</Text>
                </View>
              )}

              <View style={styles.jobFooter}>
                <Text style={styles.budgetText}>Paid: SDG {job.budget?.toLocaleString()}</Text>
                <Text style={styles.dateText}>Completed {job.postedDate}</Text>
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
    backgroundColor: '#F3F4F6',
  },
  header: {
    backgroundColor: '#0F766E',
    paddingTop: 60,
    paddingBottom: 20,
    paddingHorizontal: 20,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#FFFFFF',
  },
  postJobButton: {
    backgroundColor: '#FFFFFF',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 8,
  },
  postJobButtonText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#0F766E',
  },
  tabs: {
    flexDirection: 'row',
    backgroundColor: '#FFFFFF',
    borderBottomWidth: 1,
    borderBottomColor: '#E5E7EB',
  },
  tab: {
    flex: 1,
    paddingVertical: 16,
    alignItems: 'center',
    borderBottomWidth: 2,
    borderBottomColor: 'transparent',
  },
  tabActive: {
    borderBottomColor: '#0F766E',
  },
  tabText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#6B7280',
  },
  tabTextActive: {
    color: '#0F766E',
  },
  scrollContent: {
    padding: 20,
  },
  jobCard: {
    backgroundColor: '#FFFFFF',
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
    fontWeight: '600',
    color: '#1F2937',
    marginRight: 8,
  },
  statusBadge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 6,
  },
  statusText: {
    fontSize: 11,
    fontWeight: '600',
  },
  jobCategory: {
    fontSize: 13,
    color: '#6B7280',
    marginBottom: 12,
  },
  applicantsRow: {
    backgroundColor: '#F3F4F6',
    padding: 10,
    borderRadius: 8,
    marginBottom: 12,
  },
  applicantsText: {
    fontSize: 14,
    color: '#374151',
    fontWeight: '500',
  },
  workerRow: {
    backgroundColor: '#ECFDF5',
    padding: 10,
    borderRadius: 8,
    marginBottom: 12,
  },
  workerText: {
    fontSize: 14,
    color: '#065F46',
    fontWeight: '500',
  },
  jobFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#F3F4F6',
  },
  budgetText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#0F766E',
  },
  dateText: {
    fontSize: 12,
    color: '#9CA3AF',
  },
});
