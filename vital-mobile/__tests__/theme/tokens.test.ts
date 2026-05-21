import { tokens } from '../../src/theme/tokens';

describe('tokens', () => {
  it('has all colour tokens', () => {
    const colors = ['bone', 'paper', 'ink', 'slate', 'mist', 'hairline', 'tealDeep', 'positive', 'warning', 'critical', 'chartLine'];
    colors.forEach((c) => expect(tokens).toHaveProperty(c));
  });

  it('bone is warm bone white', () => {
    expect(tokens.bone).toBe('#F7F4ED');
  });

  it('tealDeep matches spec', () => {
    expect(tokens.tealDeep).toBe('#2D5F5D');
  });

  it('has spacing tokens', () => {
    expect(tokens.s8).toBe(8);
    expect(tokens.s16).toBe(16);
    expect(tokens.s32).toBe(32);
  });

  it('has radii', () => {
    expect(tokens.radii.card).toBe(8);
    expect(tokens.radii.button).toBe(10);
  });

  it('has category accent colors', () => {
    expect(tokens.categoryColors.medication).toBe('#4A5D7E');
    expect(tokens.categoryColors.water).toBe('#5B8A8F');
    expect(tokens.categoryColors.workout).toBe('#8B5A3C');
  });

  it('hairline is editorial warm', () => {
    expect(tokens.hairline).toBe('#E8E3D8');
  });
});
