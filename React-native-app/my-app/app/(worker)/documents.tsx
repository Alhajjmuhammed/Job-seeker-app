import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  Linking,
  Modal,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import * as DocumentPicker from 'expo-document-picker';
import { useTheme } from '../../contexts/ThemeContext';
import Header from '../../components/Header';
import apiService from '../../services/api';

interface Document {
  id: number;
  title: string;
  document_type: string;
  file_url: string;
  verification_status: 'verified' | 'pending' | 'rejected';
  uploaded_at: string;
  rejection_reason?: string;
}

interface DocumentTypeOption {
  type: 'id' | 'cv' | 'certificate' | 'license' | 'other';
  label: string;
  icon: keyof typeof Ionicons.glyphMap;
  required?: boolean;
}

export default function DocumentsScreen() {
  const { theme, isDark } = useTheme();
  const [loading, setLoading] = useState(false);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [hasNationalId, setHasNationalId] = useState(false);
  const [showTypeSelector, setShowTypeSelector] = useState(false);

  useEffect(() => {
    loadDocuments();
  }, []);

  const loadDocuments = async () => {
    try {
      setLoading(true);
      const response = await apiService.getWorkerDocuments();
      setDocuments(response.documents || []);
      setHasNationalId(response.has_national_id || false);
    } catch (error) {
      console.error('Error loading documents:', error);
      Alert.alert('Error', 'Failed to load documents');
    } finally {
      setLoading(false);
    }
  };

  const handleUploadDocument = () => {
    // Get already uploaded document types
    const uploadedTypes = documents.map(doc => doc.document_type);
    
    // Check if all types are uploaded
    const allTypesUploaded = ['id', 'cv', 'certificate', 'license'].every(type => 
      uploadedTypes.includes(type)
    );
    
    if (allTypesUploaded) {
      Alert.alert(
        'All Documents Uploaded',
        'You have already uploaded all required document types. You can only add more "Other" documents or delete existing ones to upload new versions.'
      );
    }
    
    // Show type selector
    setShowTypeSelector(true);
  };

  const getAvailableDocumentTypes = (): DocumentTypeOption[] => {
    const uploadedTypes = documents.map(doc => doc.document_type);
    const allTypes: DocumentTypeOption[] = [
      { type: 'id', label: 'National ID Card', icon: 'card-outline', required: true },
      { type: 'cv', label: 'CV/Resume', icon: 'document-text-outline' },
      { type: 'certificate', label: 'Certificate', icon: 'school-outline' },
      { type: 'license', label: 'License', icon: 'ribbon-outline' },
      { type: 'other', label: 'Other Document', icon: 'folder-outline' },
    ];
    
    return allTypes.filter(docType => 
      docType.type === 'other' || !uploadedTypes.includes(docType.type)
    );
  };

  const handleSelectDocumentType = async (documentType: 'id' | 'cv' | 'certificate' | 'license' | 'other') => {
    setShowTypeSelector(false);
    
    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: ['image/*', 'application/pdf'],
        copyToCacheDirectory: true,
      });

      if (result.canceled) {
        return;
      }

      const file = result.assets[0];
      await uploadFile(file, documentType);
    } catch (error) {
      console.error('Error picking document:', error);
      Alert.alert('Error', 'Failed to pick document');
    }
  };

  const uploadFile = async (file: any, documentType: 'id' | 'cv' | 'certificate' | 'license' | 'other') => {
    try {
      setLoading(true);

      const fileToUpload: any = {
        uri: file.uri,
        type: file.mimeType || 'application/octet-stream',
        name: file.name,
      };

      await apiService.uploadDocument(fileToUpload, documentType);
      Alert.alert('Success', 'Document uploaded successfully!');
      loadDocuments(); // Reload the list
    } catch (error: any) {
      console.error('Upload error:', error);
      Alert.alert('Upload Failed', error.response?.data?.error || 'Failed to upload document');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteDocument = (doc: Document) => {
    Alert.alert(
      'Delete Document',
      `Are you sure you want to delete "${doc.title}"?`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            try {
              setLoading(true);
              await apiService.deleteDocument(doc.id);
              Alert.alert('Success', 'Document deleted successfully');
              loadDocuments(); // Reload the list
            } catch (error: any) {
              console.error('Delete error:', error);
              Alert.alert('Error', error.response?.data?.error || 'Failed to delete document');
            } finally {
              setLoading(false);
            }
          },
        },
      ]
    );
  };

  const handleViewDocument = (doc: Document) => {
    if (doc.file_url) {
      Linking.openURL(doc.file_url).catch(() => {
        Alert.alert('Error', 'Unable to open document');
      });
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
  };

  const getDocumentTypeLabel = (type: string) => {
    const labels: { [key: string]: string } = {
      'id': 'National ID',
      'cv': 'CV/Resume',
      'certificate': 'Certificate',
      'license': 'License',
      'other': 'Other Document',
    };
    return labels[type] || type;
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
            <Ionicons name="cloud-upload-outline" size={20} color="#FFFFFF" style={{ marginRight: 8 }} />
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
                  <TouchableOpacity 
                    style={[styles.documentIcon, { backgroundColor: isDark ? theme.border : '#F3F4F6' }]}
                    onPress={() => handleViewDocument(doc)}
                  >
                    <Ionicons name="document-text-outline" size={24} color={theme.primary} />
                  </TouchableOpacity>
                  <View style={styles.documentInfo}>
                    <Text style={[styles.documentName, { color: theme.text }]}>{doc.title}</Text>
                    <Text style={[styles.documentType, { color: theme.textSecondary }]}>{getDocumentTypeLabel(doc.document_type)}</Text>
                    <Text style={[styles.documentDate, { color: theme.textSecondary }]}>Uploaded {formatDate(doc.uploaded_at)}</Text>
                    {doc.rejection_reason && (
                      <Text style={[styles.rejectionReason, { color: '#DC2626' }]}>
                        Reason: {doc.rejection_reason}
                      </Text>
                    )}
                  </View>
                  <View style={styles.documentRight}>
                    <View style={[styles.statusBadge, getStatusStyle(doc.verification_status)]}>
                      <Ionicons 
                        name={getStatusIcon(doc.verification_status) as any} 
                        size={14} 
                        color={getStatusStyle(doc.verification_status).color} 
                        style={{ marginRight: 4 }}
                      />
                      <Text style={[styles.statusText, { color: getStatusStyle(doc.verification_status).color }]}>
                        {doc.verification_status}
                      </Text>
                    </View>
                    <TouchableOpacity
                      style={styles.deleteButton}
                      onPress={() => handleDeleteDocument(doc)}
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

      {/* Document Type Selector Modal */}
      <Modal
        visible={showTypeSelector}
        transparent={true}
        animationType="slide"
        onRequestClose={() => setShowTypeSelector(false)}
      >
        <TouchableOpacity 
          style={styles.modalOverlay} 
          activeOpacity={1}
          onPress={() => setShowTypeSelector(false)}
        >
          <View style={[styles.modalContent, { backgroundColor: theme.card }]}>
            <View style={styles.modalHeader}>
              <Text style={[styles.modalTitle, { color: theme.text }]}>Select Document Type</Text>
              <TouchableOpacity onPress={() => setShowTypeSelector(false)}>
                <Ionicons name="close" size={24} color={theme.text} />
              </TouchableOpacity>
            </View>
            
            <ScrollView style={styles.optionsList}>
              {getAvailableDocumentTypes().map((docType) => (
                <TouchableOpacity
                  key={docType.type}
                  style={[styles.optionItem, { borderBottomColor: theme.border }]}
                  onPress={() => handleSelectDocumentType(docType.type)}
                >
                  <View style={[styles.optionIconContainer, { backgroundColor: theme.primary + '20' }]}>
                    <Ionicons name={docType.icon} size={24} color={theme.primary} />
                  </View>
                  <View style={styles.optionTextContainer}>
                    <Text style={[styles.optionLabel, { color: theme.text }]}>
                      {docType.label}
                    </Text>
                    {docType.required && (
                      <Text style={[styles.requiredBadge, { color: '#DC2626' }]}>Required</Text>
                    )}
                  </View>
                  <Ionicons name="chevron-forward" size={20} color={theme.textSecondary} />
                </TouchableOpacity>
              ))}
            </ScrollView>
          </View>
        </TouchableOpacity>
      </Modal>
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
  rejectionReason: {
    fontSize: 12,
    fontFamily: 'Poppins_400Regular',
    color: '#DC2626',
    marginTop: 4,
    fontStyle: 'italic',
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
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: '#FFFFFF',
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    paddingBottom: 34,
    maxHeight: '70%',
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#E5E7EB',
  },
  modalTitle: {
    fontSize: 18,
    fontFamily: 'Poppins_600SemiBold',
    color: '#1F2937',
  },
  optionsList: {
    padding: 16,
  },
  optionItem: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#E5E7EB',
  },
  optionIconContainer: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: '#D1FAE5',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  optionTextContainer: {
    flex: 1,
  },
  optionLabel: {
    fontSize: 16,
    fontFamily: 'Poppins_500Medium',
    color: '#1F2937',
  },
  requiredBadge: {
    fontSize: 12,
    fontFamily: 'Poppins_400Regular',
    color: '#DC2626',
    marginTop: 2,
  },
});
