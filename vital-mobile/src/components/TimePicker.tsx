import { useState } from 'react';
import { Pressable, Platform, Modal, View, Button } from 'react-native';
import DateTimePicker from '@react-native-community/datetimepicker';
import { Text } from './Text';
import { tokens } from '../theme/tokens';

interface TimePickerProps {
    value: string; // "HH:mm"
    onChange: (time: string) => void;
}

function parseTime(time: string): Date {
    const [h, m] = time.split(':').map(Number);
    const d = new Date();
    d.setHours(h, m, 0, 0);
    return d;
}

function formatTime(date: Date): string {
    return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;
}

export function TimePicker({ value, onChange }: TimePickerProps) {
    const [show, setShow] = useState(false);

    const handleChange = (event: any, selectedDate?: Date) => {
        // Android dismisses the modal on OK/Cancel, so hide it automatically
        if (Platform.OS === 'android') {
            setShow(false);
        }

        // Only fire onChange if the user didn't dismiss the picker
        if (event.type !== 'dismissed' && selectedDate) {
            onChange(formatTime(selectedDate));
        }
    };

    return (
        <>
            <Pressable
                onPress={() => setShow(true)}
                style={{ borderWidth: 1, borderColor: tokens.hairline, borderRadius: tokens.radii.card, padding: tokens.s12 }}
            >
                <Text variant="mono" color="ink">{value}</Text>
            </Pressable>

            {/* ANDROID */}
            {show && Platform.OS === 'android' && (
                <DateTimePicker
                    mode="time"
                    value={parseTime(value)}
                    display="spinner"
                    onChange={handleChange}
                />
            )}

            {/* IOS */}
            {show && Platform.OS === 'ios' && (
                <Modal transparent animationType="slide">
                    <View style={{ flex: 1, justifyContent: 'flex-end', backgroundColor: 'rgba(0,0,0,0.5)' }}>
                        {/* You can replace this background color with tokens.background if you have one */}
                        <View style={{ backgroundColor: 'white', paddingBottom: 20 }}>
                            <View style={{ alignItems: 'flex-end', padding: 10 }}>
                                <Button title="Done" onPress={() => setShow(false)} />
                            </View>
                            <DateTimePicker
                                mode="time"
                                value={parseTime(value)}
                                display="spinner"
                                onChange={handleChange}
                            />
                        </View>
                    </View>
                </Modal>
            )}
        </>
    );
}