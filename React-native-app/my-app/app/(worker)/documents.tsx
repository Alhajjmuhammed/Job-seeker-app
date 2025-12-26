import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../contexts/ThemeContext';
import Header from '../../components/Header';

interface Document {
  id: number;
  name: string;
  type: string;
  uploadDate: string;
  status: 'verified' | 'pending' | 'rejected';
}

export default function DocumentsScreen() {
  const { theme, isDark } = useTheme();
  const [loading, setLoading] = useState(false);
  const [documents, setDocuments] = useState<Document[]>([]);

  useEffect(() => {
    loadDocuments();
  }, []);

  const loadDocuments = async () => {
    try {
      setLoading(true);
      // TODO: Implement getDocuments API endpoint
      // const docs = await apiService.getWorkerDocuments();
      // setDocuments(docs);
      
      // Mock data for now
      setDocuments([]);
    } catch (error) {
      console.error('Error loading documents:', error);
      Alert.alert('Error', 'Failed to load documents');
    } finally {
      setLoading(false);
    }
  };

  const handleUploadDocument = () => {
    Alert.alert('Upload Document', 'Document upload feature coming soon!');
  };

  const handleDeleteDocument = (docId: number) => {
    Alert.alert(
      'Delete Document',
      'Are you sure you want to delete this document?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            try {
              // TODO: Implement deleteDocument API endpoint
              // await apiService.deleteDocument(docId);
              setDocuments(documents.filter(doc => doc.id !== docId));
              Alert.alert('Success', 'Document deleted');
            } catch (error) {
              Alert.alert('Error', 'Failed to delete document');
            }
          },
        },
      ]
    );
  };

  const getStatusStyle = (status: string) => {
    switch (status) {
      case 'verified':
        return { backgroundColor: '#D1FAE5', color: '#065F46' };
      case 'pending':
        return { backgroundColor: '#FEF3C7', color: '#92400E' };
      case 'rejected':
        return { backgroundColor: '#FEE2E2', color: '#991B1B' };
      default:
        return { backgroundColor: '#F3F4F6', color: '#6B7280' };
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'verified':
        return 'checkmark-circle';
      case 'pending':
        return 'time-outline';
      case 'rejected':
        return 'close-circle';
      default:
        return 'document-text-outline';
    }
  };

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      <StatusBar style={theme.statusBar} />
      
      {/* Header Component */}
      <Header 
        showNotifications 
        showSearch 
        onNotificationPress={() => Alert.alert('Notifications', 'No new notifications')}
        onSearchPress={() => Alert.alert('Search', 'Search coming soon')}
      />

      {loading ? (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={theme.primary} />
          <Text style={[styles.loadingText, { color: theme.textSecondary }]}>Loading documents...</Text>
        </View>
      ) : (
        <ScrollView contentContainerStyle={styles.scrollContent}>
          {/* Info Banner */}
          <View style={[styles.infoBanner, { backgroundColor: isDark ? 'rgba(59, 130, 246, 0.1)' : '#EFF6FF', borderLeftColor: theme.primary }]}>
            <Text style={styles.infoIcon}>📋</Text>
            <Text style={[styles.infoText, { color: isDark ? '#93C5FD' : '#1E40AF' }]}>
              <Text style={[styles.requiredText, { color: isDark ? '#FCA5A5' : '#DC2626' }]}>Required:</Text> National ID only.{'\n'}
              <Text style={[styles.optionalText, { color: isDark ? '#6EE7B7' : '#059669' }]}>Optional:</Text> Certificates, degrees, and proof of experience.
            </Text>
          </View>

          {/* Upload Button */}
          <TouchableOpacity style={[styles.uploadButton, { backgroundColor: theme.primary }]} onPress={handleUploadDocument}>
            <Text style={styles.uploadIcon}>📤</Text>
            <Text style={styles.uploadButtonText}>Upload Document</Text>
          </TouchableOpacity>

          {/* Documents List */}
          <View style={styles.section}>
            <Text style={[styles.sectionTitle, { color: theme.text }]}>Uploaded Documents</Text>
            {documents.length === 0 ? (
              <View style={[styles.emptyState, { backgroundColor: theme.surface, shadowColor: isDark ? '#000' : '#000', shadowOpacity: isDark ? 0.3 : 0.1 }]}>
                <Ionicons name="document-text-outline" size={48} color={theme.textSecondary} />
                <Text style={[styles.emptyText, { color: theme.text }]}>No documents uploaded</Text>
                <Text style={[styles.emptySubtext, { color: theme.textSecondary }]}>
                  Upload documents to verify your profile
                </Text>
              </View>
            ) : (
              documents.map((doc) => (
                <View key={doc.id} style={[styles.documentCard, { backgroundColor: theme.surface, shadowColor: isDark ? '#000' : '#000', shadowOpacity: isDark ? 0.3 : 0.1 }]}>
                  <View style={[styles.documentIcon, { backgroundColor: isDark ? theme.border : '#F3F4F6' }]}>
                    <Ionicons name="document-text-outline" size={24} color={theme.primary} />
                  </View>
                  <View style={styles.documentInfo}>
                    <Text style={[styles.documentName, { color: theme.text }]}>{doc.name}</Text>
                    <Text style={[styles.documentType, { color: theme.textSecondary }]}>{doc.type}</Text>
                    <Text style={[styles.documentDate, { color: theme.textSecondary }]}>Uploaded {doc.uploadDate}</Text>
                  </View>
                  <View style={styles.documentRight}>
                    <View style={[styles.statusBadge, getStatusStyle(doc.status)]}>
                      <Ionicons 
                        name={getStatusIcon(doc.status) as any} 
                        size={14} 
                        color={getStatusStyle(doc.status).color} 
                        style={{ marginRight: 4 }}
                      />
                      <Text style={[styles.statusText, { color: getStatusStyle(doc.status).color }]}>
                        {doc.status}
                      </Text>
                    </View>
                    <TouchableOpacity
                      style={styles.deleteButton}
                      onPress={() => handleDeleteDocument(doc.id)}
                    >
                      <Text style={styles.deleteButtonText}>Delete</Text>
                    </TouchableOpacity>
                  </View>
                </View>
              ))
            )}
          </View>

          {/* Document Guidelines */}
          <View style={[styles.guideSection, { backgroundColor: theme.surface, shadowColor: isDark ? '#000' : '#000', shadowOpacity: isDark ? 0.3 : 0.1 }]}>
            <Text style={[styles.guideTitle, { color: theme.text }]}>Document Guidelines</Text>
            
            <Text style={[styles.guideSectionTitle, { color: theme.text }]}>🔴 Required (Must Upload)</Text>
            <View style={styles.guideItem}>
              <Ionicons name="checkmark" size={16} color={theme.primary} style={{ marginRight: 8 }} />
              <Text style={[styles.guideText, { color: theme.textSecondary }]}>National ID or Passport</Text>
            </View>

            <Text style={[styles.guideSectionTitle, { color: theme.text }]}>⚪ Optional (Recommended)</Text>
            <View style={styles.guideItem}>
              <Text style={[styles.guideIcon, { color: theme.textSecondary }]}>•</Text>
              <Text style={[styles.guideText, { color: theme.textSecondary }]}>Professional Certificates (for professionals)</Text>
            </View>
            <View style={styles.guideItem}>
              <Text style={[styles.guideIcon, { color: theme.textSecondary }]}>•</Text>
              <Text style={[styles.guideText, { color: theme.textSecondary }]}>University Degrees (for professionals)</Text>
            </View>
            <View style={styles.guideItem}>
              <Text style={[styles.guideIcon, { color: theme.textSecondary }]}>•</Text>
              <Text style={[styles.guideText, { color: theme.textSecondary }]}>Proof of Experience (for non-academic workers)</Text>
            </View>
          </View>
        </ScrollView>
      )}
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
    paddingTop: 50,
    paddingBottom: 20,
    paddingHorizontal: 20,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  backButton: {
    width: 40,
  },
  backIcon: {
    fontSize: 28,
    fontFamily: 'Poppins_400Regular',
    color: '#FFFFFF',
  },
  headerTitle: {
    fontSize: 20,
    fontFamily: 'Poppins_700Bold',
    color: '#FFFFFF',
  },
  headerRight: {
    width: 40,
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
    color: '#6B7280',
  },
  scrollContent: {
    padding: 20,
  },
  infoBanner: {
    backgroundColor: '#EFF6FF',
    borderRadius: 12,
    padding: 16,
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 20,
    borderLeftWidth: 4,
    borderLeftColor: '#3B82F6',
  },
  infoIcon: {
    fontSize: 24,
    fontFamily: 'Poppins_400Regular',
    marginRight: 12,
  },
  infoText: {
    flex: 1,
    fontSize: 14,
    fontFamily: 'Poppins_400Regular',
    color: '#1E40AF',
    lineHeight: 20,
  },
  uploadButton: {
    backgroundColor: '#0F766E',
    borderRadius: 12,
    padding: 16,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 24,
  },
  uploadIcon: {
    fontSize: 20,
    fontFamily: 'Poppins_400Regular',
    marginRight: 8,
  },
  uploadButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontFamily: 'Poppins_700Bold',
  },
  section: {
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 18,
    fontFamily: 'Poppins_700Bold',
    color: '#1F2937',
    marginBottom: 12,
  },
  emptyState: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 40,
    alignItems: 'center',
  },
  emptyIcon: {
    fontSize: 48,
    fontFamily: 'Poppins_400Regular',
    marginBottom: 12,
  },
  emptyText: {
    fontSize: 16,
    fontFamily: 'Poppins_600SemiBold',
    color: '#1F2937',
    marginBottom: 4,
  },
  emptySubtext: {
    fontSize: 14,
    fontFamily: 'Poppins_400Regular',
    color: '#6B7280',
  },
  documentCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    flexDirection: 'row',
    alignItems: 'center',
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
  },
  documentIcon: {
    width: 48,
    height: 48,
    borderRadius: 8,
    backgroundColor: '#F3F4F6',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  documentIconText: {
    fontSize: 24,
    fontFamily: 'Poppins_400Regular',
  },
  documentInfo: {
    flex: 1,
  },
  documentName: {
    fontSize: 16,
    fontFamily: 'Poppins_600SemiBold',
    color: '#1F2937',
    marginBottom: 4,
  },
  documentType: {
    fontSize: 14,
    fontFamily: 'Poppins_400Regular',
    color: '#6B7280',
    marginBottom: 2,
  },
  documentDate: {
    fontSize: 12,
    fontFamily: 'Poppins_400Regular',
    color: '#9CA3AF',
  },
  documentRight: {
    alignItems: 'flex-end',
  },
  statusBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 6,
    marginBottom: 8,
  },
  statusText: {
    fontSize: 12,
    fontFamily: 'Poppins_600SemiBold',
    textTransform: 'capitalize',
  },
  deleteButton: {
    paddingHorizontal: 12,
    paddingVertical: 4,
  },
  deleteButtonText: {
    fontSize: 12,
    fontFamily: 'Poppins_400Regular',
    color: '#EF4444',
  },
  guideSection: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 20,
  },
  guideTitle: {
    fontSize: 16,
    fontFamily: 'Poppins_700Bold',
    color: '#1F2937',
    marginBottom: 16,
  },
  guideItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  guideIcon: {
    fontSize: 16,
    fontFamily: 'Poppins_400Regular',
    color: '#059669',
    marginRight: 12,
    width: 20,
  },
  requiredText: {
    fontFamily: 'Poppins_700Bold',
    color: '#DC2626',
  },
  optionalText: {
    fontFamily: 'Poppins_700Bold',
    color: '#059669',
  },
  guideSectionTitle: {
    fontSize: 14,
    fontFamily: 'Poppins_600SemiBold',
    color: '#1F2937',
    marginTop: 12,
    marginBottom: 8,
  },
  guideText: {
    fontSize: 14,
    fontFamily: 'Poppins_400Regular',
    color: '#4B5563',
    flex: 1,
  },
});
