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
        return '✓';
      case 'pending':
        return '⏳';
      case 'rejected':
        return '✗';
      default:
        return '📄';
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
          <ActivityIndicator size="large" color="#0F766E" />
          <Text style={styles.loadingText}>Loading documents...</Text>
        </View>
      ) : (
        <ScrollView contentContainerStyle={styles.scrollContent}>
          {/* Info Banner */}
          <View style={styles.infoBanner}>
            <Text style={styles.infoIcon}>📋</Text>
            <Text style={styles.infoText}>
              <Text style={styles.requiredText}>Required:</Text> National ID only.{'\n'}
              <Text style={styles.optionalText}>Optional:</Text> Certificates, degrees, and proof of experience.
            </Text>
          </View>

          {/* Upload Button */}
          <TouchableOpacity style={styles.uploadButton} onPress={handleUploadDocument}>
            <Text style={styles.uploadIcon}>📤</Text>
            <Text style={styles.uploadButtonText}>Upload Document</Text>
          </TouchableOpacity>

          {/* Documents List */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Uploaded Documents</Text>
            {documents.length === 0 ? (
              <View style={styles.emptyState}>
                <Text style={styles.emptyIcon}>📄</Text>
                <Text style={styles.emptyText}>No documents uploaded</Text>
                <Text style={styles.emptySubtext}>
                  Upload documents to verify your profile
                </Text>
              </View>
            ) : (
              documents.map((doc) => (
                <View key={doc.id} style={styles.documentCard}>
                  <View style={styles.documentIcon}>
                    <Text style={styles.documentIconText}>📄</Text>
                  </View>
                  <View style={styles.documentInfo}>
                    <Text style={styles.documentName}>{doc.name}</Text>
                    <Text style={styles.documentType}>{doc.type}</Text>
                    <Text style={styles.documentDate}>Uploaded {doc.uploadDate}</Text>
                  </View>
                  <View style={styles.documentRight}>
                    <View style={[styles.statusBadge, getStatusStyle(doc.status)]}>
                      <Text style={[styles.statusText, { color: getStatusStyle(doc.status).color }]}>
                        {getStatusIcon(doc.status)} {doc.status}
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
          <View style={styles.guideSection}>
            <Text style={styles.guideTitle}>Document Guidelines</Text>
            
            <Text style={styles.guideSectionTitle}>🔴 Required (Must Upload)</Text>
            <View style={styles.guideItem}>
              <Text style={styles.guideIcon}>✓</Text>
              <Text style={styles.guideText}>National ID or Passport</Text>
            </View>

            <Text style={styles.guideSectionTitle}>⚪ Optional (Recommended)</Text>
            <View style={styles.guideItem}>
              <Text style={styles.guideIcon}>•</Text>
              <Text style={styles.guideText}>Professional Certificates (for professionals)</Text>
            </View>
            <View style={styles.guideItem}>
              <Text style={styles.guideIcon}>•</Text>
              <Text style={styles.guideText}>University Degrees (for professionals)</Text>
            </View>
            <View style={styles.guideItem}>
              <Text style={styles.guideIcon}>•</Text>
              <Text style={styles.guideText}>Proof of Experience (for non-academic workers)</Text>
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
    fontWeight: 'bold',
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
    fontWeight: 'bold',
  },
  section: {
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 18,
    fontFamily: 'Poppins_700Bold',
    fontWeight: 'bold',
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
    fontWeight: '600',
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
    fontWeight: '600',
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
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 6,
    marginBottom: 8,
  },
  statusText: {
    fontSize: 12,
    fontFamily: 'Poppins_600SemiBold',
    fontWeight: '600',
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
    fontWeight: 'bold',
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
    fontWeight: 'bold',
    color: '#DC2626',
  },
  optionalText: {
    fontWeight: 'bold',
    color: '#059669',
  },
  guideSectionTitle: {
    fontSize: 14,
    fontFamily: 'Poppins_600SemiBold',
    fontWeight: '600',
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
