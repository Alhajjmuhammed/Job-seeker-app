import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  TextInput,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { router } from 'expo-router';

interface Job {
  id: number;
  title: string;
  category: string;
  client: string;
  rate: number;
  location: string;
  postedDate: string;
  applicants: number;
}

export default function WorkerJobsScreen() {
  const [activeTab, setActiveTab] = useState<'browse' | 'applications'>('browse');
  const [searchQuery, setSearchQuery] = useState('');

  const [availableJobs] = useState<Job[]>([
    {
      id: 1,
      title: 'Fix Kitchen Sink Leak',
      category: 'Plumbing',
      client: 'Ahmed Hassan',
      rate: 500,
      location: 'Khartoum',
      postedDate: '2 hours ago',
      applicants: 3,
    },
    {
      id: 2,
      title: 'Install Ceiling Fan',
      category: 'Electrical',
      client: 'Fatima Ali',
      rate: 600,
      location: 'Omdurman',
      postedDate: '5 hours ago',
      applicants: 7,
    },
    {
      id: 3,
      title: 'Paint Living Room',
      category: 'Painting',
      client: 'Ibrahim Omar',
      rate: 3000,
      location: 'Bahri',
      postedDate: '1 day ago',
      applicants: 12,
    },
  ]);

  const [myApplications] = useState([
    {
      id: 1,
      title: 'Repair Bathroom Tiles',
      category: 'Construction',
      client: 'Sara Mohammed',
      status: 'pending',
      appliedDate: '2 days ago',
    },
    {
      id: 2,
      title: 'Fix Air Conditioner',
      category: 'HVAC',
      client: 'Omar Ali',
      status: 'accepted',
      appliedDate: '1 week ago',
    },
  ]);

  return (
    <View style={styles.container}>
      <StatusBar style="light" />
      
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Jobs</Text>
      </View>

      {/* Tabs */}
      <View style={styles.tabs}>
        <TouchableOpacity
          style={[styles.tab, activeTab === 'browse' && styles.tabActive]}
          onPress={() => setActiveTab('browse')}
        >
          <Text style={[styles.tabText, activeTab === 'browse' && styles.tabTextActive]}>
            Browse Jobs
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.tab, activeTab === 'applications' && styles.tabActive]}
          onPress={() => setActiveTab('applications')}
        >
          <Text style={[styles.tabText, activeTab === 'applications' && styles.tabTextActive]}>
            My Applications
          </Text>
        </TouchableOpacity>
      </View>

      <ScrollView contentContainerStyle={styles.scrollContent}>
        {activeTab === 'browse' ? (
          <>
            {/* Search Bar */}
            <View style={styles.searchContainer}>
              <TextInput
                style={styles.searchInput}
                placeholder="Search jobs..."
                value={searchQuery}
                onChangeText={setSearchQuery}
              />
            </View>

            {/* Filter Buttons */}
            <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.filters}>
              {['All', 'Plumbing', 'Electrical', 'Carpentry', 'Painting', 'Cleaning'].map(
                (filter) => (
                  <TouchableOpacity key={filter} style={styles.filterButton}>
                    <Text style={styles.filterText}>{filter}</Text>
                  </TouchableOpacity>
                )
              )}
            </ScrollView>

            {/* Available Jobs */}
            {availableJobs.map((job) => (
              <TouchableOpacity
                key={job.id}
                style={styles.jobCard}
                onPress={() => router.push(`/(worker)/job/${job.id}`)}
              >
                <View style={styles.jobHeader}>
                  <View style={styles.jobTitleContainer}>
                    <Text style={styles.jobTitle}>{job.title}</Text>
                    <Text style={styles.jobCategory}>{job.category}</Text>
                  </View>
                  <View style={styles.rateBadge}>
                    <Text style={styles.rateText}>SDG {job.rate}</Text>
                  </View>
                </View>

                <View style={styles.jobDetails}>
                  <Text style={styles.clientName}>👤 {job.client}</Text>
                  <Text style={styles.location}>📍 {job.location}</Text>
                </View>

                <View style={styles.jobFooter}>
                  <Text style={styles.postedDate}>{job.postedDate}</Text>
                  <Text style={styles.applicants}>{job.applicants} applicants</Text>
                </View>
              </TouchableOpacity>
            ))}
          </>
        ) : (
          <>
            {/* My Applications */}
            {myApplications.map((application) => (
              <View key={application.id} style={styles.applicationCard}>
                <View style={styles.applicationHeader}>
                  <View style={styles.applicationTitleContainer}>
                    <Text style={styles.applicationTitle}>{application.title}</Text>
                    <Text style={styles.applicationCategory}>{application.category}</Text>
                  </View>
                  <View
                    style={[
                      styles.statusBadge,
                      application.status === 'accepted' && styles.statusAccepted,
                      application.status === 'pending' && styles.statusPending,
                    ]}
                  >
                    <Text
                      style={[
                        styles.statusText,
                        application.status === 'accepted' && styles.statusTextAccepted,
                      ]}
                    >
                      {application.status === 'accepted' ? '✓ Accepted' : '⏳ Pending'}
                    </Text>
                  </View>
                </View>

                <Text style={styles.applicationClient}>Client: {application.client}</Text>
                <Text style={styles.applicationDate}>Applied {application.appliedDate}</Text>
              </View>
            ))}
          </>
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
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#FFFFFF',
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
  searchContainer: {
    marginBottom: 16,
  },
  searchInput: {
    height: 48,
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    paddingHorizontal: 16,
    fontSize: 15,
    borderWidth: 1,
    borderColor: '#E5E7EB',
  },
  filters: {
    marginBottom: 20,
  },
  filterButton: {
    backgroundColor: '#FFFFFF',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    marginRight: 8,
    borderWidth: 1,
    borderColor: '#E5E7EB',
  },
  filterText: {
    fontSize: 13,
    fontWeight: '600',
    color: '#6B7280',
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
    marginBottom: 12,
  },
  jobTitleContainer: {
    flex: 1,
    marginRight: 12,
  },
  jobTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1F2937',
    marginBottom: 4,
  },
  jobCategory: {
    fontSize: 13,
    color: '#6B7280',
  },
  rateBadge: {
    backgroundColor: '#ECFDF5',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 8,
  },
  rateText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#0F766E',
  },
  jobDetails: {
    marginBottom: 12,
  },
  clientName: {
    fontSize: 14,
    color: '#374151',
    marginBottom: 4,
  },
  location: {
    fontSize: 14,
    color: '#6B7280',
  },
  jobFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#F3F4F6',
  },
  postedDate: {
    fontSize: 12,
    color: '#9CA3AF',
  },
  applicants: {
    fontSize: 12,
    color: '#9CA3AF',
  },
  applicationCard: {
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
  applicationHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  applicationTitleContainer: {
    flex: 1,
    marginRight: 12,
  },
  applicationTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1F2937',
    marginBottom: 4,
  },
  applicationCategory: {
    fontSize: 13,
    color: '#6B7280',
  },
  statusBadge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 6,
  },
  statusAccepted: {
    backgroundColor: '#D1FAE5',
  },
  statusPending: {
    backgroundColor: '#FEF3C7',
  },
  statusText: {
    fontSize: 11,
    fontWeight: '600',
    color: '#92400E',
  },
  statusTextAccepted: {
    color: '#065F46',
  },
  applicationClient: {
    fontSize: 14,
    color: '#374151',
    marginBottom: 4,
  },
  applicationDate: {
    fontSize: 12,
    color: '#9CA3AF',
  },
});
