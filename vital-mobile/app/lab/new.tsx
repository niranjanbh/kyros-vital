import { DateInput } from '../../src/components/DateInput';
import React, { useState } from 'react';
import {
  Alert,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  View,
} from 'react-native';
import { router } from 'expo-router';
import { ArrowLeft, Camera, FileText, Image as ImageLibIcon, Plus, Trash2 } from 'lucide-react-native';
import * as ImagePicker from 'expo-image-picker';
import * as DocumentPicker from 'expo-document-picker';
import { format } from 'date-fns';
import { useQueryClient } from '@tanstack/react-query';

import { tokens } from '../../src/theme/tokens';
import { Text } from '../../src/components/Text';
import { Input } from '../../src/components/Input';
import { Button } from '../../src/components/Button';
import { FormField } from '../../src/components/FormField';
import { Card } from '../../src/components/Card';
import { getOrCreateDeviceId } from '../../src/api/client';

const FLAG_OPTIONS = ['normal', 'low', 'high', 'critical'] as const;
type Flag = (typeof FLAG_OPTIONS)[number];

const FLAG_ABBR: Record<Flag, string> = { normal: 'N', low: 'L', high: 'H', critical: 'C' };
const FLAG_COLORS: Record<Flag, string> = {
  normal:   tokens.positive,
  low:      tokens.warning,
  high:     tokens.warning,
  critical: tokens.critical,
};

interface TestRow {
  id: string;
  name: string;
  value: string;
  unit: string;
  ref_low: string;
  ref_high: string;
  flag: Flag;
}

function makeRow(): TestRow {
  return {
    id: Math.random().toString(36).slice(2),
    name: '', value: '', unit: '', ref_low: '', ref_high: '', flag: 'normal',
  };
}

export default function NewLabReportScreen() {
  const [labName, setLabName] = useState('');
  const [reportDate, setReportDate] = useState(new Date());
  const [note, setNote] = useState('');
  const [tests, setTests] = useState<TestRow[]>([makeRow()]);
  const [file, setFile] = useState<{ uri: string; name: string; mime: string } | null>(null);
  const [progress, setProgress] = useState(0);
  const [uploading, setUploading] = useState(false);
  const qc = useQueryClient();

  const pickCamera = async () => {
    const result = await ImagePicker.launchCameraAsync({ mediaTypes: ['images'], quality: 0.85 });
    if (!result.canceled && result.assets[0]) {
      const a = result.assets[0];
      setFile({ uri: a.uri, name: a.fileName ?? 'photo.jpg', mime: a.mimeType ?? 'image/jpeg' });
    }
  };

  const pickGallery = async () => {
    const result = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ['images'], quality: 0.85 });
    if (!result.canceled && result.assets[0]) {
      const a = result.assets[0];
      setFile({ uri: a.uri, name: a.fileName ?? 'photo.jpg', mime: a.mimeType ?? 'image/jpeg' });
    }
  };

  const pickPDF = async () => {
    const result = await DocumentPicker.getDocumentAsync({ type: 'application/pdf' });
    if (!result.canceled && result.assets[0]) {
      const a = result.assets[0];
      setFile({ uri: a.uri, name: a.name, mime: a.mimeType ?? 'application/pdf' });
    }
  };

  const updateTest = (id: string, field: keyof TestRow, value: string) =>
    setTests((prev) => prev.map((t) => (t.id === id ? { ...t, [field]: value } : t)));

  const handleSubmit = async () => {
    if (!file) {
      Alert.alert('Validation', 'Please select a file.');
      return;
    }
    const validTests = tests.filter((t) => t.name.trim());
    if (validTests.length === 0) {
      Alert.alert('Validation', 'Add at least one named test result.');
      return;
    }

    const parsed = validTests.map((t) => ({
      name: t.name.trim(),
      value: t.value.trim(),
      unit: t.unit.trim(),
      ref_low: t.ref_low ? parseFloat(t.ref_low) : null,
      ref_high: t.ref_high ? parseFloat(t.ref_high) : null,
      flag: t.flag,
    }));

    const metadata = {
      report_date: format(reportDate, 'yyyy-MM-dd'),
      lab_name: labName.trim() || null,
      parsed,
      note: note.trim() || null,
    };

    const formData = new FormData();
    formData.append('file', { uri: file.uri, name: file.name, type: file.mime } as any);
    formData.append('metadata', JSON.stringify(metadata));

    setUploading(true);
    setProgress(0);

    try {
      const deviceId = await getOrCreateDeviceId();
      const BASE_URL = process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000';

      await new Promise<void>((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open('POST', `${BASE_URL}/v1/wellness/lab-reports/`);
        xhr.setRequestHeader('X-Device-Id', deviceId);
        xhr.upload.onprogress = (e) => {
          if (e.lengthComputable) setProgress(e.loaded / e.total);
        };
        xhr.onload = () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            resolve();
          } else {
            try {
              reject(new Error((JSON.parse(xhr.responseText) as any).detail ?? 'Upload failed'));
            } catch {
              reject(new Error(`Upload failed (${xhr.status})`));
            }
          }
        };
        xhr.onerror = () => reject(new Error('Network error. Check your connection.'));
        xhr.send(formData);
      });

      qc.invalidateQueries({ queryKey: ['lab-reports'] });
      router.back();
    } catch (e: any) {
      setUploading(false);
      Alert.alert('Upload failed', e?.message ?? 'Something went wrong.', [
        { text: 'Retry', onPress: () => void handleSubmit() },
        { text: 'Cancel', style: 'cancel' },
      ]);
    }
  };

  return (
    <SafeAreaView style={styles.safe}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        style={{ flex: 1 }}
      >
        <View style={styles.header}>
          <Pressable onPress={() => router.back()} hitSlop={12}>
            <ArrowLeft size={22} color={tokens.ink} strokeWidth={1.5} />
          </Pressable>
          <Text variant="h1" color="ink" style={styles.title}>New Lab Report</Text>
          <View style={{ width: 22 }} />
        </View>

        <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
          {/* File picker */}
          <FormField label="File">
            {file ? (
              <View style={styles.filePreview}>
                <Text variant="body" color="ink" numberOfLines={1} style={{ flex: 1 }}>
                  {file.name}
                </Text>
                <Pressable onPress={() => setFile(null)} hitSlop={8}>
                  <Trash2 size={16} color={tokens.critical} strokeWidth={1.5} />
                </Pressable>
              </View>
            ) : (
              <View style={styles.fileButtons}>
                <Pressable style={styles.fileBtn} onPress={pickCamera}>
                  <Camera size={18} color={tokens.slate} strokeWidth={1.5} />
                  <Text variant="caption" color="slate">Camera</Text>
                </Pressable>
                <Pressable style={styles.fileBtn} onPress={pickGallery}>
                  <ImageLibIcon size={18} color={tokens.slate} strokeWidth={1.5} />
                  <Text variant="caption" color="slate">Gallery</Text>
                </Pressable>
                <Pressable style={styles.fileBtn} onPress={pickPDF}>
                  <FileText size={18} color={tokens.slate} strokeWidth={1.5} />
                  <Text variant="caption" color="slate">PDF</Text>
                </Pressable>
              </View>
            )}
          </FormField>

          {/* Lab name */}
          <FormField label="Lab Name (optional)">
            <Input
              value={labName}
              onChangeText={setLabName}
              placeholder="e.g. Quest Diagnostics"
            />
          </FormField>

          {/* Report date */}
          <FormField label="Report Date">
            <DateInput value={reportDate} onChange={setReportDate} maximumDate={new Date()} />
          </FormField>

          {/* Tests */}
          <View>
            <View style={styles.testsSectionHead}>
              <Text variant="label" color="mist" style={styles.sectionLabel}>TESTS</Text>
              <Pressable
                onPress={() => setTests((p) => [...p, makeRow()])}
                hitSlop={8}
                style={styles.addRow}
              >
                <Plus size={14} color={tokens.tealDeep} strokeWidth={1.5} />
                <Text variant="caption" color="tealDeep">Add row</Text>
              </Pressable>
            </View>
            {tests.map((test, idx) => (
              <TestEditor
                key={test.id}
                test={test}
                index={idx}
                canRemove={tests.length > 1}
                onChange={(f, v) => updateTest(test.id, f, v)}
                onRemove={() => setTests((p) => p.filter((t) => t.id !== test.id))}
              />
            ))}
          </View>

          {/* Note */}
          <FormField label="Note (optional)">
            <Input
              value={note}
              onChangeText={setNote}
              placeholder="e.g. Fasting panel"
              multiline
              style={{ minHeight: 64, textAlignVertical: 'top' }}
            />
          </FormField>

          {/* Progress bar */}
          {uploading && (
            <View style={styles.progressWrapper}>
              <View style={styles.progressTrack}>
                <View style={[styles.progressFill, { flex: progress }]} />
                <View style={{ flex: 1 - progress }} />
              </View>
              <Text variant="caption" color="mist" style={{ marginTop: tokens.s4, textAlign: 'center' }}>
                Uploading… {Math.round(progress * 100)}%
              </Text>
            </View>
          )}

          <Button
            onPress={handleSubmit}
            variant="primary"
            style={styles.saveBtn}
            disabled={uploading}
          >
            {uploading ? 'Uploading…' : 'Save Report'}
          </Button>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

// ── Test row editor ────────────────────────────────────────────────────────────

function TestEditor({
  test, index, canRemove, onChange, onRemove,
}: {
  test: TestRow;
  index: number;
  canRemove: boolean;
  onChange: (field: keyof TestRow, value: string) => void;
  onRemove: () => void;
}) {
  return (
    <Card style={styles.testCard}>
      <View style={styles.testCardHead}>
        <Text variant="caption" color="mist" style={{ letterSpacing: 0.5 }}>
          TEST {index + 1}
        </Text>
        {canRemove && (
          <Pressable onPress={onRemove} hitSlop={8}>
            <Trash2 size={14} color={tokens.critical} strokeWidth={1.5} />
          </Pressable>
        )}
      </View>

      <View style={styles.testRow}>
        <InlineInput label="Name" value={test.name} onChangeText={(v) => onChange('name', v)} placeholder="HbA1c" flex={2} />
        <InlineInput label="Value" value={test.value} onChangeText={(v) => onChange('value', v)} placeholder="5.6" flex={1} numeric />
        <InlineInput label="Unit" value={test.unit} onChangeText={(v) => onChange('unit', v)} placeholder="%" flex={1} />
      </View>

      <View style={[styles.testRow, { marginTop: tokens.s8 }]}>
        <InlineInput label="Ref Low" value={test.ref_low} onChangeText={(v) => onChange('ref_low', v)} placeholder="—" flex={1} numeric />
        <InlineInput label="Ref High" value={test.ref_high} onChangeText={(v) => onChange('ref_high', v)} placeholder="—" flex={1} numeric />
        <View style={{ flex: 1 }}>
          <Text variant="caption" color="mist" style={styles.inlineLabel}>Flag</Text>
          <View style={styles.flagChips}>
            {FLAG_OPTIONS.map((f) => (
              <Pressable
                key={f}
                style={[
                  styles.flagChip,
                  test.flag === f && {
                    borderColor: FLAG_COLORS[f],
                    backgroundColor: `${FLAG_COLORS[f]}18`,
                  },
                ]}
                onPress={() => onChange('flag', f)}
              >
                <Text
                  variant="caption"
                  style={{
                    color: test.flag === f ? FLAG_COLORS[f] : tokens.mist,
                    fontFamily: 'GeistMono-Regular',
                    fontSize: 10,
                  }}
                >
                  {FLAG_ABBR[f]}
                </Text>
              </Pressable>
            ))}
          </View>
        </View>
      </View>
    </Card>
  );
}

function InlineInput({
  label, value, onChangeText, placeholder, flex, numeric,
}: {
  label: string;
  value: string;
  onChangeText: (v: string) => void;
  placeholder: string;
  flex: number;
  numeric?: boolean;
}) {
  return (
    <View style={{ flex }}>
      <Text variant="caption" color="mist" style={styles.inlineLabel}>{label}</Text>
      <Input
        value={value}
        onChangeText={onChangeText}
        placeholder={placeholder}
        keyboardType={numeric ? 'decimal-pad' : 'default'}
        style={styles.testInput}
      />
    </View>
  );
}

// ── styles ────────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: tokens.bone },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: tokens.s20,
    paddingTop: tokens.s16,
    paddingBottom: tokens.s8,
  },
  title: { flex: 1, textAlign: 'center' },
  content: {
    paddingHorizontal: tokens.s20,
    paddingTop: tokens.s16,
    paddingBottom: tokens.s48,
    gap: tokens.s24,
  },
  filePreview: {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: tokens.hairline,
    borderRadius: tokens.radii.card,
    padding: tokens.s12,
    backgroundColor: tokens.paper,
    gap: tokens.s8,
  },
  fileButtons: {
    flexDirection: 'row',
    gap: tokens.s8,
  },
  fileBtn: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: tokens.s4,
    paddingVertical: tokens.s16,
    borderWidth: 1,
    borderColor: tokens.hairline,
    borderRadius: tokens.radii.card,
    backgroundColor: tokens.paper,
  },
  dateBtn: {
    borderWidth: 1,
    borderColor: tokens.hairline,
    borderRadius: tokens.radii.card,
    padding: tokens.s12,
    backgroundColor: tokens.paper,
  },
  testsSectionHead: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: tokens.s8,
  },
  sectionLabel: { textTransform: 'uppercase', letterSpacing: 1 },
  addRow: { flexDirection: 'row', alignItems: 'center', gap: tokens.s4 },
  testCard: { marginBottom: tokens.s8, gap: tokens.s8 },
  testCardHead: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  testRow: { flexDirection: 'row', gap: tokens.s8 },
  testInput: { padding: tokens.s8, fontSize: 13 },
  inlineLabel: { marginBottom: tokens.s4, textTransform: 'uppercase', letterSpacing: 0.5, fontSize: 10 },
  flagChips: { flexDirection: 'row', gap: tokens.s4, flexWrap: 'wrap' },
  flagChip: {
    width: 22,
    height: 22,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: tokens.hairline,
    borderRadius: 4,
    backgroundColor: tokens.paper,
  },
  progressWrapper: { gap: tokens.s4 },
  progressTrack: {
    height: 4,
    backgroundColor: tokens.hairline,
    borderRadius: 2,
    overflow: 'hidden',
    flexDirection: 'row',
  },
  progressFill: {
    height: 4,
    backgroundColor: tokens.tealDeep,
    borderRadius: 2,
  },
  saveBtn: { marginTop: tokens.s8 },
});
